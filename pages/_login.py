import streamlit as st
from utils.mongo_helper import validate_login
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

        /* Hide all navigation elements */
        .stDeployButton {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}

        /* Hide full-screen button */
        [data-testid="stElementToolbar"] {
        display: none !important;
        }
       
    </style>
""", unsafe_allow_html=True)

# If already authenticated, redirect to overview
if st.session_state.is_authenticated:
    st.switch_page("pages/1_🏠_Overview.py")

# Create three columns for centering
colA, colB, colC = st.columns([1, 2, 1])
with colB:
    try:
        st.image("images/Logo.png", width=120, use_container_width=True)
    except:
        st.title("Fitlistic")

    st.markdown("<h1 style='text-align: center; font-size: 2rem;'>Welcome Back</h1>",
                unsafe_allow_html=True)

# Add some spacing
st.write("")

# Login Container
with st.container():
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password")
            elif len(username) < 3:
                st.error("Username must be at least 3 characters")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                success, user = validate_login(username, password)

                if success and user is not None:  # Explizit auf None prüfen
                    st.session_state.user = user
                    st.session_state.is_authenticated = True
                    st.success("Login successful! Redirecting...")
                    st.switch_page("pages/1_🏠_Overview.py")
                else:
                    st.error("Invalid username or password")

    with col2:
        if st.button("Register", use_container_width=True):
            st.switch_page("pages/_Register.py")
