import streamlit as st
from utils.mongo_helper import UserManager
import re

# Page config
st.set_page_config(
    page_title="Fitlistic - Register",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Create three columns for centering
col1, col2, col3 = st.columns([1, 2, 1])

# Use the middle column for logo and title
with col2:
    try:
        st.image("images/Logo.png", width=120, use_container_width=True)
    except:
        st.title("Fitlistic")
    st.markdown("<h1 style='text-align: center; font-size: 2rem;'>Create Account</h1>", unsafe_allow_html=True)

# Add some spacing
st.write("")

# Registration Form
with st.form("register_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        first_name = st.text_input("First Name")
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)

    with col2:
        last_name = st.text_input("Last Name")
        email = st.text_input("Email").strip().lower()
        password_confirm = st.text_input("Confirm Password", type="password")
        weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=70)

    # Fitness goals selection
    goals = st.multiselect(
        "Your Fitness Goals",
        ["Weight Loss", "Muscle Gain", "Flexibility", "Endurance", "General Fitness"]
    )

    # Buttons vertically aligned
    submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)
    back = st.form_submit_button("Back to Login", use_container_width=True)

# Process form submission
if submit:
    if not all([username, email, password, password_confirm, first_name, last_name]):
        st.error("Please fill in all required fields")

    elif password != password_confirm:
        st.error("Passwords do not match")

    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Please enter a valid email address")

    elif len(password) < 8:
        st.error("Password must be at least 8 characters long")

    else:
        user_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "height": height,
            "weight": weight,
            "fitness_goals": goals,
            "profile_completed": True
        }

        user_mgr = UserManager()
        success, message = user_mgr.create_user(username, password, user_data)

        if success:
            st.success("Account created successfully! Redirecting to login...")
            st.switch_page("pages/login.py")
        else:
            st.error(message)

# Handle back button
if back:
    st.switch_page("pages/login.py")