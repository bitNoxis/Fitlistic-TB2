import streamlit as st

from utils.auth_helper import auth_required


@auth_required
def aicoach_page():
    # Page config
    st.set_page_config(page_title="AI Wellbeing Coach", page_icon="✨", layout="centered")

    # Main content
    st.title(f"Hey, {st.session_state.user['first_name']}!")

    # Session Options
    st.header("Quick Start")


# Run the page
aicoach_page()
