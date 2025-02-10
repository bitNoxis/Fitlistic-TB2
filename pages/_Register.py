import streamlit as st
from utils.mongo_helper import create_user
import re


# Page config
st.set_page_config(
    page_title="Fitlistic - Register",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        /* Hide sidebar navigation */
        div[data-testid="stSidebarNav"] {display: none !important;}

        /* Hide menu button */
        button[kind="header"] {display: none !important;}

        /* Hide hamburger menu */
        .stApp > header {display: none !important;}

        /* Hide Streamlit footer */
        footer {display: none !important;}

        /* Optional: Hide all navigation elements */
        .stDeployButton {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}

        /* Keep the rest of your theme styling */
        .stButton > button {
            width: 100%;
            border-radius: 5px;
            height: 2.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for form fields and touched states
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'first_name': '',
        'last_name': '',
        'username': '',
        'email': '',
        'password': '',
        'password_confirm': '',
        'height': 170,
        'weight': 70,
        'goals': []
    }

if 'touched' not in st.session_state:
    st.session_state.touched = {}


# Validation functions
def validate_email(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Please enter a valid email address"
    return None


def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    return None


def validate_passwords_match(password, confirm):
    if password != confirm:
        return "Passwords do not match"
    return None


def validate_required(value, field_name):
    if not value:
        return f"{field_name} is required"
    return None


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
col1, col2 = st.columns(2)

with col1:
    # First Name
    first_name = st.text_input("First Name", key="first_name")
    if first_name:
        st.session_state.touched['first_name'] = True
    if st.session_state.touched.get('first_name', False) and not first_name:
        st.error("First Name is required")

    # Username
    username = st.text_input("Username", key="username").strip().lower()
    if username:
        st.session_state.touched['username'] = True
    if st.session_state.touched.get('username', False) and not username:
        st.error("Username is required")

    # Password
    password = st.text_input("Password", type="password", key="password")
    if password:
        st.session_state.touched['password'] = True
    if st.session_state.touched.get('password', False):
        error = validate_password(password)
        if error:
            st.error(error)

    height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)

with col2:
    # Last Name
    last_name = st.text_input("Last Name", key="last_name")
    if last_name:
        st.session_state.touched['last_name'] = True
    if st.session_state.touched.get('last_name', False) and not last_name:
        st.error("Last Name is required")

    # Email
    email = st.text_input("Email", key="email").strip().lower()
    if email:
        st.session_state.touched['email'] = True
    if st.session_state.touched.get('email', False):
        error = validate_email(email)
        if error:
            st.error(error)

    # Confirm Password
    password_confirm = st.text_input("Confirm Password", type="password", key="password_confirm")
    if password_confirm:
        st.session_state.touched['password_confirm'] = True
    if st.session_state.touched.get('password_confirm', False):
        error = validate_passwords_match(password, password_confirm)
        if error:
            st.error(error)

    weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=70)

# Fitness goals selection
goals = st.multiselect(
    "Your Fitness Goals",
    ["Weight Loss", "Muscle Gain", "Flexibility", "Endurance", "General Fitness"]
)

# Check if form is valid
form_is_valid = all([
    first_name, last_name, username, email,
    password, password_confirm,
    len(password) >= 8,
    password == password_confirm,
    re.match(r"[^@]+@[^@]+\.[^@]+", email)
])

# Buttons vertically aligned
if st.button("Create Account", type="primary", use_container_width=True, disabled=not form_is_valid):
    user_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "height": height,
        "weight": weight,
        "fitness_goals": goals,
        "profile_completed": True
    }

    success, message = create_user(username, password, user_data)

    if success:
        st.success("Account created successfully! Redirecting to login...")
        st.switch_page("pages/_login.py")
    else:
        st.error(message)

if st.button("Back to Login", use_container_width=True):
    st.switch_page("pages/_login.py")
