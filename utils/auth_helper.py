import streamlit as st
from functools import wraps


def check_auth():
    # Check if user is authenticated
    return st.session_state.get('is_authenticated', False) and st.session_state.get('user', None) is not None


def auth_required(func):
    # Require authentication for pages

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_auth():
            st.switch_page("pages/_login.py")
        return func(*args, **kwargs)

    return wrapper


def init_auth():
    # Initialize authentication state
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None


def logout():
    # Clear authentication state
    st.session_state.is_authenticated = False
    st.session_state.user = None
    st.switch_page("pages/_login.py")
