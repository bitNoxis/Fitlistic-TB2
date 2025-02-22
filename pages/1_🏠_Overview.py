from datetime import datetime, timezone, timedelta

import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from bson import ObjectId
from streamlit_star_rating import st_star_rating

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection, get_latest_wellbeing_score


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
    st.title(f"Welcome, {user_name}!")

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
                range=[1, 5],
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

    # ------------------- Well-Being Score Section -------------------
    st.header("Your Latest Well-Being Score")
    try:
        latest_score = get_latest_wellbeing_score(str(user["_id"]))
        if latest_score is not None:
            st.subheader(f"Latest Score: {latest_score} / 5")
        else:
            st.info("No well-being score recorded yet.")
    except Exception as e:
        st.error(f"Error retrieving well-being score: {e}")

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
        st.info("You have already logged your mood for today!")
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
    st.header("Quick Start")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Fullbody Workout", type="primary", key="fullbody"):
            st.switch_page("pages/2_💪_Exercise.py")
        if st.button("Power Recovery", type="primary", key="recovery"):
            st.switch_page("pages/2_💪_Exercise.py")
    with col2:
        if st.button("Upperbody Workout", type="primary", key="upperbody"):
            st.switch_page("pages/2_💪_Exercise.py")
        if st.button("Lower Body", type="primary", key="lowerbody"):
            st.switch_page("pages/2_💪_Exercise.py")

        # ------------------- Weekly Progress Section (Workout Stats) -------------------
        st.header("Weekly Progress")
        try:
            workout_collection = get_collection("fitlistic", "workout_logs")
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            # Fetch all workout logs for the user in the last 7 days
            logs = list(workout_collection.find({
                "user_id": ObjectId(user["_id"]),
                "date": {"$gte": seven_days_ago}
            }))
            workouts_completed = len(logs)
            total_minutes = sum(log.get("total_duration_minutes", 0) for log in logs)
            total_calories = sum(log.get("total_calories_burned", 0) for log in logs)
        except Exception as e:
            st.error(f"Error fetching workout logs: {e}")
            workouts_completed = total_minutes = total_calories = 0

        if workouts_completed > 0:
            col1, col2, col3 = st.columns(2)
            with col1:
                st.metric("Workouts", workouts_completed)
            with col2:
                st.metric("Minutes", total_minutes)
            with col3:
                st.metric("Calories", total_calories)
        else:
            st.info("No workouts logged in the last 7 days. Get started by logging your first workout!")


# Run the page
overview_page()
