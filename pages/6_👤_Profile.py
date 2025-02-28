"""
Profile Management Module

This module provides functionality for managing user profiles,
including editing personal data, fitness goals, and account settings.
"""

import streamlit as st
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from bson.objectid import ObjectId

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection, verify_password, hash_password

# Constants
DB_NAME = "fitlistic"
USER_COLLECTION = "users"
DEFAULT_HEIGHT = 0
DEFAULT_WEIGHT = 0
FITNESS_GOALS = [
    "Flexibility",
    "Better Mental Health",
    "Stress Resilience",
    "General Fitness",
    "Weight Loss",
    "Muscle Gain"
]


def get_account_age(created_at: datetime) -> str:
    """
    Calculate how long an account has existed.

    Args:
        created_at: Account creation date

    Returns:
        Formatted string with number of days
    """
    try:
        now = datetime.now(timezone.utc)

        # Ensure created_at has timezone info
        if created_at.tzinfo is None:
            import pytz
            created_at = pytz.utc.localize(created_at)

        days = (now - created_at).days
        return f"{days} days"
    except Exception:
        return "{0:%B %d, %Y}".format(created_at)


def update_profile_data(user_id: Union[str, ObjectId], update_data: Dict[str, Any]) -> bool:
    """
    Update user profile data in MongoDB.

    Args:
        user_id: User ID
        update_data: Data to update

    Returns:
        Boolean indicating success
    """
    try:
        collection = get_collection(DB_NAME, USER_COLLECTION)
        if collection is None:
            return False

        # Convert user_id to ObjectId if it's a string
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        # Update the user document
        result = collection.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )

        return result.modified_count > 0
    except Exception as e:
        st.error(f"Error updating profile: {str(e)}")
        return False


def verify_and_update_password(
        user_id: Union[str, ObjectId],
        current_password: str,
        new_password: str
) -> bool:
    """
    Verify current password and update to new password if correct.

    Args:
        user_id: User ID
        current_password: Current password
        new_password: New password

    Returns:
        Boolean indicating success
    """
    try:
        collection = get_collection(DB_NAME, USER_COLLECTION)
        if collection is None:
            return False

        # Convert user_id to ObjectId if it's a string
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        # Get user document
        user = collection.find_one({"_id": user_id})
        if not user:
            return False

        # Verify current password
        if not verify_password(current_password, user["password"]):
            return False

        # Hash new password
        hashed_pw, salt = hash_password(new_password)

        # Update password
        result = collection.update_one(
            {"_id": user_id},
            {"$set": {"password": hashed_pw, "salt": salt}}
        )

        return result.modified_count > 0
    except Exception as e:
        st.error(f"Error updating password: {str(e)}")
        return False


def refresh_user_session(user_id: Union[str, ObjectId]) -> bool:
    """
    Update user data in session with latest data from database.

    Args:
        user_id: User ID

    Returns:
        Boolean indicating success
    """
    collection = get_collection(DB_NAME, USER_COLLECTION)
    if collection is None:
        return False

    # Convert user_id to ObjectId if it's a string
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    # Get updated user data
    updated_user = collection.find_one({"_id": user_id})

    if updated_user:
        # Convert ObjectId to string for session state compatibility
        updated_user["_id"] = str(updated_user["_id"])
        # Update entire user session state
        st.session_state.user = updated_user
        return True

    return False


def handle_logout() -> None:
    """
    Handle logout process by clearing session state.
    """
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("You have been logged out successfully.")
    st.rerun()


def display_sidebar_options() -> None:
    """
    Display quick options in the sidebar.
    """
    with st.sidebar:
        st.header("Quick Options")

        if st.button("Log Out", key="sidebar_logout"):
            handle_logout()

        if st.button("Create New Account"):
            st.switch_page("pages/_Register.py")


def display_profile_info_tab(user: Dict[str, Any]) -> None:
    """
    Display profile information tab.

    Args:
        user: User data dictionary
    """
    user_id = user.get("_id")

    # Basic user info
    st.subheader(f"{user.get('first_name', '')} {user.get('last_name', '')}")
    st.write(f"**Username:** {user.get('username', '')}")
    st.write(f"**Email:** {user.get('email', '')}")

    # Account age
    if user.get("created_at"):
        account_age = get_account_age(user.get("created_at"))
        st.write(f"**Member for:** {account_age}")

    # Physical stats section with edit functionality
    st.subheader("Physical Stats & Fitness Goals")

    # Physical stats
    col1, col2 = st.columns(2)
    with col1:
        current_height = user.get("height", DEFAULT_HEIGHT)
        new_height = st.number_input("Height (cm)", min_value=0, max_value=300, value=current_height, step=1)

    with col2:
        current_weight = user.get("weight", DEFAULT_WEIGHT)
        new_weight = st.number_input("Weight (kg)", min_value=0, max_value=500, value=current_weight, step=1)

    # Fitness goals
    st.write("**Your Fitness Goals:**")
    current_goals = user.get("fitness_goals", [])

    # Display as multiselect
    selected_goals = st.multiselect(
        "Select your fitness goals",
        FITNESS_GOALS,
        default=current_goals,
        key="fitness_goals"
    )

    # Save changes button for both stats and goals
    if ((new_height != current_height or new_weight != current_weight or
         set(selected_goals) != set(current_goals)) and
            st.button("Update Stats & Goals", key="update_stats_button")):

        update_data = {
            "height": new_height,
            "weight": new_weight,
            "fitness_goals": selected_goals
        }

        if update_profile_data(user_id, update_data):
            refresh_user_session(user_id)
            st.success("Profile information updated successfully!")
            st.rerun()
        else:
            st.error("Error updating profile information.")


def display_account_settings_tab(user: Dict[str, Any]) -> None:
    """
    Display account settings tab.

    Args:
        user: User data dictionary
    """
    user_id = user.get("_id")

    st.subheader("Account Settings")

    # Account details that can be edited
    with st.form(key="account_form"):
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name", value=user.get("first_name", ""))

        with col2:
            last_name = st.text_input("Last Name", value=user.get("last_name", ""))

        email = st.text_input("Email", value=user.get("email", ""))

        # Form submission button
        submit = st.form_submit_button("Update Account Details")

        if submit:
            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email.lower()
            }

            if update_profile_data(user_id, update_data):
                if refresh_user_session(user_id):
                    st.success("Account details updated successfully!")
                else:
                    # Fallback to just updating the specific fields
                    st.session_state.user.update(update_data)
                    st.success("Account details updated successfully!")
            else:
                st.error("Failed to update account details.")

    # Change password section
    st.subheader("Change Password")

    with st.form(key="password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")

        password_submit = st.form_submit_button("Change Password")

        if password_submit:
            if not current_password or not new_password or not confirm_password:
                st.error("All password fields are required.")
            elif new_password != confirm_password:
                st.error("New password and confirmation do not match.")
            else:
                # Verify current password and update
                if verify_and_update_password(user_id, current_password, new_password):
                    refresh_user_session(user_id)
                    st.success("Password updated successfully!")
                else:
                    st.error("Current password is incorrect or there was an error updating your password.")


@auth_required
def profile_page() -> None:
    """
    Main function for the profile page.

    This page allows users to manage their profile information, account details,
    and passwords.
    """
    # Page config
    st.set_page_config(page_title="Profile | Fitlistic", page_icon="👤", layout="centered")
    inject_custom_styles()

    # Main title
    st.title("👤 Profile Management")
    st.header("Edit your profile details like goals and more")

    # Display sidebar options
    display_sidebar_options()

    # Get user from session state
    if "user" not in st.session_state:
        st.error("You must be logged in to view this page")
        return

    user = st.session_state.user

    # Logout button below title but above tabs
    if st.button("Log Out", type="primary", key="main_logout"):
        handle_logout()

    # Container for the main content
    with st.container():
        # Create tabs for different sections
        tab1, tab2 = st.tabs(["Profile Info", "Account Settings"])

        # Tab 1: Profile Info
        with tab1:
            display_profile_info_tab(user)

        # Tab 2: Account Settings
        with tab2:
            display_account_settings_tab(user)


# Run the main function
profile_page()
