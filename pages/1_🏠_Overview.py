import streamlit as st
from PIL import Image
from utils.helpers import check_user_name

# Page config
st.set_page_config(page_title="Overview", page_icon="🏠", layout="centered")

# Check if user has entered name
user_name = check_user_name()

# Main content
st.title(f"Welcome back, {user_name}")

# Wellbeing Score Section
st.header("Wellbeing Score")
try:
    score_img = Image.open("images/Score.png")
    st.image(score_img, width=335)
except:
    st.warning("Score image not found")

# Session Options
st.header("Quick Start")

col1, col2 = st.columns(2)
with col1:
    st.button("Fullbody Workout", type="primary", key="fullbody")
    st.button("Power Recovery", type="primary", key="recovery")

with col2:
    st.button("Upperbody Workout", type="primary", key="upperbody")
    st.button("Lower Body", type="primary", key="lowerbody")

# Weekly Progress
st.header("Weekly Progress")
progress_data = {
    'Workouts Completed': 3,
    'Total Minutes': 45,
    'Calories Burned': 450
}

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Workouts", progress_data['Workouts Completed'])
with col2:
    st.metric("Minutes", progress_data['Total Minutes'])
with col3:
    st.metric("Calories", progress_data['Calories Burned'])