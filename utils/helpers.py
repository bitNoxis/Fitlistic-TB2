"""Helper functions and constants for the Fitlistic app"""
# Motivational quotes
QUOTATIONS = {
    1: "Exercises is king and nutrition is queen. Combine the two and you will have a kingdom.",
    2: "The only bad workout is the one that didn't happen.",
    3: "Fitness is not about being better than someone else. It's about being better than you used to be."
}


def check_user_name():
    """Ensure user has entered their name before accessing pages"""
    import streamlit as st

    if 'user_name' not in st.session_state or not st.session_state.user_name:
        st.warning("Please enter your name on the home page first!")
        st.stop()

    return st.session_state.user_name
