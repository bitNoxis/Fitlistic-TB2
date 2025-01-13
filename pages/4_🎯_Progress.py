import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from utils.auth_helper import auth_required


@auth_required
def progress_page():
    # Page config
    st.set_page_config(page_title="Progress", page_icon="🎯", layout="wide")

    # Initialize demo data if not exists
    if 'workout_history' not in st.session_state:
        # Create demo data for the last 30 days
        dates = [datetime.today() - timedelta(days=x) for x in range(30)]
        st.session_state.workout_history = pd.DataFrame({
            'date': dates,
            'workouts': [int(x % 3 == 0) for x in range(30)],  # workout every 3 days
            'minutes': [45 if x % 3 == 0 else 0 for x in range(30)],
            'calories': [450 if x % 3 == 0 else 0 for x in range(30)]
        })

    # Main content
    st.title("Your Fitness Progress")

    # Time period selection
    time_period = st.selectbox(
        "Select Time Period",
        ["Last 7 Days", "Last 30 Days", "Last 3 Months", "Last Year"]
    )

    # Filter data based on selected time period
    df = st.session_state.workout_history.copy()
    df['date'] = pd.to_datetime(df['date'])

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Workouts", df['workouts'].sum())
    with col2:
        st.metric("Total Minutes", df['minutes'].sum())
    with col3:
        st.metric("Total Calories", df['calories'].sum())
    with col4:
        workout_streak = (df['workouts'] != 0).sum()
        st.metric("Current Streak", f"{workout_streak} days")

    # Workout Calendar Heatmap
    st.subheader("Workout Calendar")
    fig = px.density_heatmap(
        df,
        x=df['date'].dt.strftime('%U'),  # Week number
        y=df['date'].dt.strftime('%A'),  # Day name
        z='workouts',
        title="Workout Frequency",
        labels={'x': 'Week', 'y': 'Day', 'z': 'Workouts'}
    )
    st.plotly_chart(fig)


# Run the page
progress_page()
