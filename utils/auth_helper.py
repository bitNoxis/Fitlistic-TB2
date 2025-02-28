"""
Authentication Utilities

This module provides functions for handling user authentication
throughout the Streamlit application, including checking auth status,
protecting pages, and managing login state.
This was created partly with the help of ChatGPT o1.
"""

import streamlit as st
from functools import wraps


def check_auth():
    """
    Check if a user is currently authenticated.

    Returns:
        bool: True if user is authenticated with valid user data, False otherwise
    """
    return st.session_state.get('is_authenticated', False) and st.session_state.get('user', None) is not None


def auth_required(func):
    """
    Decorator that requires authentication for accessing pages.

    If user is not authenticated, redirects to login page.

    Args:
        func: The function to wrap with authentication checking

    Returns:
        function: Wrapped function that checks authentication before execution
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_auth():
            st.switch_page("pages/_login.py")
        return func(*args, **kwargs)

    return wrapper


def init_auth():
    """
    Initialize authentication state variables in session state.

    Creates 'is_authenticated' and 'user' if they don't exist.
    """
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None


def logout():
    """
    Log out the current user by clearing authentication state.

    Resets authentication variables and redirects to login page.
    """
    st.session_state.is_authenticated = False
    st.session_state.user = None
    st.switch_page("pages/_login.py")
