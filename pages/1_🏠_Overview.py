"""
Overview Page Module

This module provides the main dashboard view for the Fitlistic application,
displaying user stats, workout data, and well-being tracking.
"""

from datetime import datetime, timezone, timedelta

import plotly.graph_objects as go
import streamlit as st
from bson import ObjectId
from streamlit_star_rating import st_star_rating

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection

# Constants
DB_NAME = "fitlistic"
WORKOUT_LOGS_COLLECTION = "workout_logs"
WELLBEING_COLLECTION = "wellbeing_scores"
DAYS_IN_WEEK = 7
DAYS_IN_MONTH = 30
MIN_ENTRIES_FOR_GRAPH = 5


def get_user_streak(user_id):
    """
    Calculate the user's current workout streak in consecutive days.

    Args:
        user_id: User ID string

    Returns:
        Integer representing consecutive days of workouts
    """
    collection = get_collection(DB_NAME, WORKOUT_LOGS_COLLECTION)
    if collection is None:
        return 0

    streak = 0
    now = datetime.now(timezone.utc)

    # Check if user worked out today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_workout = collection.find_one({
        "user_id": ObjectId(user_id),
        "date": {"$gte": today_start, "$lt": today_end}
    })

    # If no workout today, check yesterday
    if not today_workout:
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)

        yesterday_workout = collection.find_one({
            "user_id": ObjectId(user_id),
            "date": {"$gte": yesterday_start, "$lt": yesterday_end}
        })

        # If no workout yesterday, no streak
        if not yesterday_workout:
            return 0

    # Start date to check (today or yesterday depending on workout today)
    check_date = today_start if today_workout else yesterday_start
    streak = 1  # Start with 1 for the most recent workout

    # Check consecutive days going backward
    while True:
        check_date_prev = check_date - timedelta(days=1)

        prev_workout = collection.find_one({
            "user_id": ObjectId(user_id),
            "date": {"$gte": check_date_prev, "$lt": check_date}
        })

        if prev_workout:
            streak += 1
            check_date = check_date_prev
        else:
            break

    return streak


def display_wellbeing_progress(user_id):
    """
    Display the user's well-being progress graph.

    Args:
        user_id: User ID string

    Returns:
        None
    """
    st.header("Your Well-Being Progress")
    try:
        # Fetch all well-being entries for this user, sorted by date ascending
        collection = get_collection(DB_NAME, WELLBEING_COLLECTION)
        wellbeing_docs = list(collection.find({"user_id": ObjectId(user_id)}).sort("date", 1))
    except Exception as e:
        st.error(f"Error fetching well-being scores: {e}")
        wellbeing_docs = []

    if len(wellbeing_docs) >= MIN_ENTRIES_FOR_GRAPH:
        # Format dates and extract scores for plotting
        dates = [doc["date"].strftime("%b %d") for doc in wellbeing_docs]
        scores = [doc.get("score", 0) for doc in wellbeing_docs]

        # Create interactive plotly chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=scores,
            mode='lines+markers',
            line=dict(color='#1E90FF', width=3, shape="spline"),  # Spline for smooth curves
            marker=dict(size=10, color='#55b82e', line=dict(width=2, color='white')),
            customdata=[doc.get("notes", "No note") for doc in wellbeing_docs],
            hovertemplate="<b>Score: %{y}</b><br>Note: %{customdata}<extra></extra>"
        ))

        # Configure chart appearance
        fig.update_layout(
            title="Well-Being Score Over Time",
            xaxis_title="Date",
            yaxis_title="Score (1-5)",
            yaxis=dict(
                range=[0.8, 5.2],
                tickmode="array",
                tickvals=[1, 2, 3, 4, 5]
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(color="#333"),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log at least 5 well-being entries to see your progress graph.")
        display_test_entries_button(user_id)


def display_test_entries_button(user_id):
    """
    Display a button to add test well-being entries for demonstration.

    Args:
        user_id: User ID string

    Returns:
        None
    """
    if st.button("Add 5 Test Entries"):
        collection = get_collection(DB_NAME, WELLBEING_COLLECTION)
        if collection is None:
            st.error("Database connection failed.")
            return

        day_offsets = [5, 4, 3, 2, 1]
        test_scores = [3, 4, 5, 4, 5]
        test_notes = [
            "Feeling a bit tired",
            "Pretty good overall",
            "Great mood!",
            "A little stressed",
            "Fantastic day"
        ]

        for offset, score, note in zip(day_offsets, test_scores, test_notes):
            date_entry = datetime.now(timezone.utc).replace(
                hour=12, minute=0, second=0, microsecond=0
            ) - timedelta(days=offset)

            doc = {
                "user_id": ObjectId(user_id),
                "date": date_entry,
                "score": score,
                "notes": note
            }
            collection.insert_one(doc)

        st.success("5 test well-being entries added! Reloading...")
        st.rerun()


def display_mood_logger(user_id):
    """
    Display the mood logging interface.

    Args:
        user_id: User ID string

    Returns:
        None
    """
    st.header("Log Your Mood")

    collection = get_collection(DB_NAME, WELLBEING_COLLECTION)
    if collection is None:
        st.error("Database connection failed.")
        return

    # Define today's range in UTC
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # Query for an entry in the current day
    found = collection.find_one({
        "user_id": ObjectId(user_id),
        "date": {
            "$gte": today_start,
            "$lt": tomorrow_start
        }
    })

    if found:
        # User has already logged a mood for today
        st.info("You have already logged your mood for today! Check back tomorrow.")
    else:
        # Show the mood logging expander
        with st.expander("Click here to log your current mood", expanded=False):
            mood_rating = st_star_rating(
                label="How do you feel today?",
                maxValue=5,
                defaultValue=3,
                key="rating",
                emoticons=True
            )
            mood_notes = st.text_area("Any additional comments?", value="")
            if st.button("Submit Mood"):
                try:
                    mood_doc = {
                        "user_id": ObjectId(user_id),
                        "date": datetime.now(timezone.utc),
                        "score": mood_rating,
                        "notes": mood_notes
                    }
                    collection.insert_one(mood_doc)
                    st.success("Your mood has been logged successfully!")
                except Exception as e:
                    st.error(f"Error logging mood: {e}")


def get_workout_logs_by_period(user_id):
    """
    Fetch workout logs for different time periods.

    Args:
        user_id: User ID string

    Returns:
        Dictionary with workout logs for different time periods
    """
    try:
        workout_collection = get_collection(DB_NAME, WORKOUT_LOGS_COLLECTION)
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=DAYS_IN_WEEK)
        thirty_days_ago = now - timedelta(days=DAYS_IN_MONTH)

        # Get all workout logs for various time periods
        week_logs = list(workout_collection.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": seven_days_ago}
        }))

        month_logs = list(workout_collection.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": thirty_days_ago}
        }))

        all_logs = list(workout_collection.find({
            "user_id": ObjectId(user_id)
        }))

        return {
            "week": week_logs,
            "month": month_logs,
            "all": all_logs
        }
    except Exception as e:
        st.error(f"Error fetching workout logs: {e}")
        return {"week": [], "month": [], "all": []}


def calculate_fitness_metrics(logs):
    """
    Calculate fitness metrics from workout logs.

    Args:
        logs: Dictionary with workout logs for different time periods

    Returns:
        Dictionary with calculated metrics
    """
    week_logs = logs["week"]
    month_logs = logs["month"]
    all_logs = logs["all"]

    workouts_week = len(week_logs)
    workouts_month = len(month_logs)
    workouts_total = len(all_logs)

    minutes_week = sum(log.get("total_duration_minutes", 0) for log in week_logs)
    minutes_month = sum(log.get("total_duration_minutes", 0) for log in month_logs)
    minutes_total = sum(log.get("total_duration_minutes", 0) for log in all_logs)

    calories_week = sum(log.get("total_calories_burned", 0) for log in week_logs)
    calories_month = sum(log.get("total_calories_burned", 0) for log in month_logs)
    calories_total = sum(log.get("total_calories_burned", 0) for log in all_logs)

    avg_time = round(minutes_total / workouts_total, 1) if workouts_total > 0 else 0

    return {
        "workouts_week": workouts_week,
        "workouts_month": workouts_month,
        "workouts_total": workouts_total,
        "minutes_week": minutes_week,
        "minutes_month": minutes_month,
        "minutes_total": minutes_total,
        "calories_week": calories_week,
        "calories_month": calories_month,
        "calories_total": calories_total,
        "avg_time": avg_time
    }


def display_fitness_stats(user_id):
    """
    Display the user's fitness statistics.

    Args:
        user_id: User ID string

    Returns:
        None
    """
    st.header("Your Fitness Stats")

    try:
        # Get workout logs
        logs = get_workout_logs_by_period(user_id)

        # Calculate metrics
        metrics = calculate_fitness_metrics(logs)

        # Get current streak
        streak = get_user_streak(user_id)

        # Show stats based on available data
        if metrics["workouts_total"] > 0:
            # Main metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Streak", f"{streak} day(s)")
            with col2:
                st.metric("Total Workouts", metrics["workouts_total"])
            with col3:
                st.metric("This Week", metrics["workouts_week"])

            # Secondary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Time", f"{metrics['minutes_total']} min")
            with col2:
                st.metric("Total Calories", f"{metrics['calories_total']} kcal")
            with col3:
                st.metric("Avg. Duration", f"{metrics['avg_time']} min")
        else:
            st.info("No workouts logged yet. Get started with your first workout!")
            if st.button("Start Your First Workout"):
                st.switch_page("pages/2_💪_Exercise.py")

    except Exception as e:
        st.error(f"Error displaying fitness stats: {e}")
        import traceback
        traceback.print_exc()


def display_sidebar_options():
    """
    Display quick action buttons in the sidebar.

    Returns:
        None
    """
    with st.sidebar:
        st.header("Quick Options")
        if st.button("Today's Workout", type="primary", key="today_workout"):
            st.switch_page("pages/2_💪_Exercise.py")
        if st.button("Do a one time Workout", type="primary", key="try"):
            st.switch_page("pages/4_✨_AI-Coach.py")
        if st.button("Get a full 7 day Workout plan", type="secondary", key="upperbody"):
            st.switch_page("pages/5_📋_Workout-Creator.py")


@auth_required
def overview_page():
    """
    Main function to display the overview dashboard.

    This page shows the user's fitness statistics, well-being progress,
    and provides a mood tracking interface.
    """
    # Configure the page
    st.set_page_config(page_title="Overview", page_icon="🏠", layout="centered")
    inject_custom_styles()

    # Get user data from session
    user = st.session_state.get("user")
    if user:
        user_name = user.get("first_name", "Friend")
        user_id = user["_id"]
    else:
        user_name = "Friend"
        user_id = None
        st.error("User data not found. Please log in again.")
        return

    # Display greeting
    st.title(f"Great to see you, {user_name}! 😊")

    # Display sidebar options
    display_sidebar_options()

    # Display well-being progress
    display_wellbeing_progress(user_id)

    # Display mood logger
    display_mood_logger(user_id)

    # Display fitness stats
    display_fitness_stats(user_id)

    # Display footer image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("images/Finish.png", width=300)
        except Exception as e:
            # If image fails to load, just skip it without displaying an error
            pass


# Run the page
overview_page()