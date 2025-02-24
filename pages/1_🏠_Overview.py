import calendar
from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from bson import ObjectId
from streamlit_star_rating import st_star_rating

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection


def get_user_streak(user_id):
    collection = get_collection("fitlistic", "workout_logs")
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


def get_activity_heatmap_data(user_id):
    collection = get_collection("fitlistic", "workout_logs")
    if collection is None:
        return []

    # Get start and end of current month
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # Get all workouts for the month
    workouts = list(collection.find({
        "user_id": ObjectId(user_id),
        "date": {"$gte": start_date, "$lte": end_date}
    }))

    # Create date to count mapping
    workout_data = {}
    for workout in workouts:
        date_str = workout["date"].strftime("%Y-%m-%d")
        if date_str in workout_data:
            workout_data[date_str]["count"] += 1
            workout_data[date_str]["duration"] += workout.get("total_duration_minutes", 0)
            workout_data[date_str]["calories"] += workout.get("total_calories_burned", 0)
        else:
            workout_data[date_str] = {
                "count": 1,
                "duration": workout.get("total_duration_minutes", 0),
                "calories": workout.get("total_calories_burned", 0)
            }

    # Create full date range for the month
    all_dates = []
    for day in range(1, last_day + 1):
        date_obj = datetime(year, month, day, tzinfo=timezone.utc)
        date_str = date_obj.strftime("%Y-%m-%d")

        if date_str in workout_data:
            all_dates.append({
                "date": date_str,
                "day": day,
                "count": workout_data[date_str]["count"],
                "duration": workout_data[date_str]["duration"],
                "calories": workout_data[date_str]["calories"]
            })
        else:
            all_dates.append({
                "date": date_str,
                "day": day,
                "count": 0,
                "duration": 0,
                "calories": 0
            })

    return all_dates


@auth_required
def overview_page():
    st.set_page_config(page_title="Overview", page_icon="🏠", layout="centered")
    inject_custom_styles()

    # Get user data from session
    user = st.session_state.get("user")
    if user:
        user_name = user.get("first_name", "Friend")
    else:
        user_name = "Friend"
    st.title(f"Great to see you, {user_name}! 😊")

    # ------------------- Well-Being Progress Graph -------------------
    st.header("Your Well-Being Progress")
    try:
        # Fetch all well-being entries for this user, sorted by date ascending
        collection = get_collection("fitlistic", "wellbeing_scores")
        wellbeing_docs = list(collection.find({"user_id": ObjectId(user["_id"])}).sort("date", 1))
    except Exception as e:
        st.error(f"Error fetching well-being scores: {e}")
        wellbeing_docs = []

    if len(wellbeing_docs) >= 5:
        dates = [doc["date"].strftime("%b %d") for doc in wellbeing_docs]
        scores = [doc.get("score", 0) for doc in wellbeing_docs]
        notes = [doc.get("notes", "No note") for doc in wellbeing_docs]

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

    st.header("Log Your Mood")

    collection = get_collection("fitlistic", "wellbeing_scores")
    if collection is None:
        st.error("Database connection failed.")
        return

    # Define today's range in UTC
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # Query for an entry in the current day
    found = collection.find_one({
        "user_id": ObjectId(user["_id"]),
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
                        "user_id": ObjectId(user["_id"]),
                        "date": datetime.now(timezone.utc),
                        "score": mood_rating,
                        "notes": mood_notes
                    }
                    collection.insert_one(mood_doc)
                    st.success("Your mood has been logged successfully!")
                except Exception as e:
                    st.error(f"Error logging mood: {e}")

    # ------------------- Quick Start Section -------------------
    st.header("Quick Options")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Today's Workout", type="primary", key="today_workout"):
            st.switch_page("pages/2_💪_Exercise.py")

    with col2:
        if st.button("Do a one time workout", type="primary", key="try"):
            st.switch_page("pages/4_✨_AI-Coach.py")

    with col3:
        if st.button("Get a full 7 day workout plan", type="primary", key="upperbody"):
            st.switch_page("pages/5_📋_Workout-Creator.py")

    # ------------------- Enhanced Weekly Progress Section -------------------
    st.header("Your Fitness Stats")

    try:
        workout_collection = get_collection("fitlistic", "workout_logs")
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Current streak
        streak = get_user_streak(user["_id"])

        # Get all workout logs for various time periods
        week_logs = list(workout_collection.find({
            "user_id": ObjectId(user["_id"]),
            "date": {"$gte": seven_days_ago}
        }))

        month_logs = list(workout_collection.find({
            "user_id": ObjectId(user["_id"]),
            "date": {"$gte": thirty_days_ago}
        }))

        all_logs = list(workout_collection.find({
            "user_id": ObjectId(user["_id"])
        }))

        # Last workout
        last_workout = None
        if all_logs:
            last_workout = max(all_logs, key=lambda x: x["date"])

        # Calculate metrics
        workouts_week = len(week_logs)
        workouts_month = len(month_logs)
        workouts_total = len(all_logs)

        minutes_week = sum(log.get("total_duration_minutes", 0) for log in week_logs)
        minutes_month = sum(log.get("total_duration_minutes", 0) for log in month_logs)
        minutes_total = sum(log.get("total_duration_minutes", 0) for log in all_logs)

        calories_week = sum(log.get("total_calories_burned", 0) for log in week_logs)
        calories_month = sum(log.get("total_calories_burned", 0) for log in month_logs)
        calories_total = sum(log.get("total_calories_burned", 0) for log in all_logs)

        # Show stats based on available data
        if workouts_total > 0:
            # Main metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Streak", f"{streak} days")
            with col2:
                st.metric("Total Workouts", workouts_total)
            with col3:
                st.metric("This Week", workouts_week)
            with col4:
                last_date = last_workout["date"].strftime("%b %d") if last_workout else "Never"
                st.metric("Last Workout", last_date)

            # Secondary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Time", f"{minutes_total} min")
            with col2:
                st.metric("Total Calories", f"{calories_total} kcal")
            with col3:
                avg_time = round(minutes_total / workouts_total, 1) if workouts_total > 0 else 0
                st.metric("Avg. Duration", f"{avg_time} min")


        else:
            st.info("No workouts logged yet. Get started with your first workout!")
            if st.button("Start Your First Workout"):
                st.switch_page("pages/2_💪_Exercise.py")

    except Exception as e:
        st.error(f"Error fetching workout stats: {e}")
        import traceback
        traceback.print_exc()


overview_page()
