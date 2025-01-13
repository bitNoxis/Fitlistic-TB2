import streamlit as st

# Configure the main page settings
st.set_page_config(
    page_title="Fitlistic",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize session state for authentication
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False

# Check authentication status and redirect accordingly
if not st.session_state.is_authenticated:
    st.switch_page("pages/login.py")
else:
    st.switch_page("pages/1_🏠_Overview.py")