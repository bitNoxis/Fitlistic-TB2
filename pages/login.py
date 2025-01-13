import streamlit as st
from utils.mongo_helper import UserManager
from utils.auth_helper import init_auth

# Initialize authentication
init_auth()

# Page config
st.set_page_config(
    page_title="Fitlistic - Login",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# If already authenticated, redirect to overview
if st.session_state.is_authenticated:
    st.switch_page("pages/1_🏠_Overview.py")

# Create three columns for centering
col1, col2, col3 = st.columns([1, 2, 1])

# Use the middle column for logo and title
with col2:
    try:
        st.image("images/Logo.png", width=120, use_container_width=True)
    except:
        st.title("Fitlistic")
    st.markdown("<h1 style='text-align: center; font-size: 2rem;'>Welcome Back!</h1>", unsafe_allow_html=True)

# Add some spacing
st.write("")

# Login Container
with st.container():
    # Login Form
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")

        # Columns for buttons
        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")
        with col2:
            register = st.form_submit_button("Register", use_container_width=True)

    # Process login
    if submit and username and password:
        if len(username) < 3:
            st.error("Username must be at least 3 characters long")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters long")
        else:
            user_mgr = UserManager()
            success, user = user_mgr.validate_login(username, password)

            if success:
                st.session_state.user = user
                st.session_state.is_authenticated = True
                st.success("Login successful! Redirecting...")
                st.switch_page("pages/1_🏠_Overview.py")
            else:
                st.error("Invalid username or password")

    # Handle registration redirect
    if register:
        st.switch_page("pages/register.py")