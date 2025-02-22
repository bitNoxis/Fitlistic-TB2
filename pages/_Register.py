import re
import streamlit as st
from utils.mongo_helper import create_user

# -----------------------------
# PAGE CONFIG & CSS
# -----------------------------
st.set_page_config(
    page_title="Fitlistic - Register",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
        /* Hide sidebar navigation */
        div[data-testid="stSidebarNav"] {display: none !important;}

        /* Hide menu button */
        button[kind="header"] {display: none !important;}

        /* Hide hamburger menu */
        .stApp > header {display: none !important;}

        /* Hide Streamlit footer */
        footer {display: none !important;}

        /* Hide all navigation elements */
        .stDeployButton {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}

        /* Hide full-screen button */
        [data-testid="stElementToolbar"] {
        display: none !important;
        }
        
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# SESSION STATE
# -----------------------------
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'first_name': '',
        'last_name': '',
        'username': '',
        'email': '',
        'password': '',
        'password_confirm': '',
        'goals': []
    }

    if 'fitness_goals' not in st.session_state:
        st.session_state.fitness_goals = st.session_state.form_data['goals']

    if 'height' not in st.session_state:
        st.session_state.height = 170

    if 'weight' not in st.session_state:
        st.session_state.weight = 70

if 'touched' not in st.session_state:
    st.session_state.touched = {}

form_data = st.session_state.form_data


# -----------------------------
# VALIDATION FUNCTIONS
# -----------------------------
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


# -----------------------------
# CENTER LOGO & TITLE
# -----------------------------
colA, colB, colC = st.columns([1, 2, 1])
with colB:
    try:
        st.image("images/Logo.png", width=120, use_container_width=True)
    except:
        st.title("Fitlistic")

    st.markdown(
        "<h1 style='text-align: center; font-size: 2rem;'>Create Account</h1>",
        unsafe_allow_html=True
    )

st.write("")  # spacing

# ------------------------------------------------
# ROW 1: FIRST NAME (LEFT), LAST NAME (RIGHT)
# ------------------------------------------------
r1c1, r1c2 = st.columns(2)

first_name = r1c1.text_input("First Name", key="first_name")
if first_name:
    st.session_state.touched['first_name'] = True
if st.session_state.touched.get('first_name', False) and not first_name:
    r1c1.error("First Name is required")

last_name = r1c2.text_input("Last Name", key="last_name")
if last_name:
    st.session_state.touched['last_name'] = True
if st.session_state.touched.get('last_name', False) and not last_name:
    r1c2.error("Last Name is required")

# ------------------------------------------------
# ROW 2: USERNAME (LEFT), EMAIL (RIGHT)
# ------------------------------------------------
r2c1, r2c2 = st.columns(2)

username = r2c1.text_input("Username", key="username").strip().lower()
if username:
    st.session_state.touched['username'] = True
if st.session_state.touched.get('username', False) and not username:
    r2c1.error("Username is required")

email = r2c2.text_input("Email", key="email").strip().lower()
if email:
    st.session_state.touched['email'] = True
if st.session_state.touched.get('email', False):
    email_error = validate_email(email)
    if email_error:
        r2c2.error(email_error)

# ------------------------------------------------
# ROW 3: PASSWORD (LEFT), CONFIRM (RIGHT)
# ------------------------------------------------
r3c1, r3c2 = st.columns(2)

password = r3c1.text_input("Password", type="password", key="password")
if password:
    st.session_state.touched['password'] = True
if st.session_state.touched.get('password', False):
    pw_error = validate_password(password)
    if pw_error:
        r3c1.error(pw_error)

password_confirm = r3c2.text_input("Confirm Password", type="password", key="password_confirm")
if password_confirm:
    st.session_state.touched['password_confirm'] = True
if st.session_state.touched.get('password_confirm', False):
    match_error = validate_passwords_match(password, password_confirm)
    if match_error:
        r3c2.error(match_error)

# ------------------------------------------------
# ROW 4: HEIGHT (LEFT), WEIGHT (RIGHT)
# ------------------------------------------------
r4c1, r4c2 = st.columns(2)
r4c1.number_input("Height (cm)", min_value=100, max_value=250, key="height")
r4c2.number_input("Weight (kg)", min_value=30, max_value=200, key="weight")

# ------------------------------------------------
# Fitness Goals (single row)
# ------------------------------------------------
goals = st.multiselect(
    "Your Fitness Goals (optional)",
    ["Flexibility", "Better Mental Health", "Stress Resilience", "General Fitness", "Weight Loss", "Muscle Gain"],
    key="fitness_goals"
)

# Update form_data after collecting inputs
form_data.update({
    'first_name': first_name,
    'last_name': last_name,
    'username': username,
    'email': email,
    'password': password,
    'password_confirm': password_confirm,
    'height': st.session_state.height,
    'weight': st.session_state.weight,
    'goals': st.session_state.fitness_goals
})

# ------------------------------------------------
# FORM VALIDATION (create_button disabled logic)
# ------------------------------------------------
form_is_valid = all([
    first_name, last_name, username, email,
    password, password_confirm,
    len(password) >= 8,
    password == password_confirm,
    re.match(r"[^@]+@[^@]+\.[^@]+", email)
])

# ------------------------------------------------
# Buttons
# ------------------------------------------------
if st.button("Create Account", type="primary", use_container_width=True, disabled=not form_is_valid):
    user_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "height": st.session_state.height,
        "weight": st.session_state.weight,
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
