"""
Workout Reminder Module

This module provides functionality for users to create, view, update,
and delete workout reminders to help maintain their fitness schedule.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection

# Constants
DB_NAME = "fitlistic"
REMINDERS_COLLECTION = "reminders"
MAX_DAYS_IN_FUTURE = 365
DEFAULT_TIME = "08:00"


def parse_time_input(time_str: str) -> Tuple[bool, Optional[datetime.time], str]:
    """
    Parse a time string input in HH:MM format.

    Args:
        time_str: Time string in HH:MM format

    Returns:
        Tuple of (is_valid, time_object, error_message)
    """
    try:
        hour, minute = map(int, time_str.split(':'))
        if 0 <= hour < 24 and 0 <= minute < 60:
            selected_time = datetime.strptime(time_str, "%H:%M").time()
            return True, selected_time, ""
        else:
            return False, None, "Invalid time format. Please use HH:MM (24-hour format)."
    except ValueError:
        return False, None, "Invalid time format. Please use HH:MM (24-hour format)."


def create_reminder(
        user_id: str,
        title: str,
        reminder_datetime: datetime,
        notes: str
) -> bool:
    """
    Create a new reminder in the database.

    Args:
        user_id: User ID string
        title: Reminder title
        reminder_datetime: Datetime of the reminder
        notes: Optional reminder notes

    Returns:
        Boolean indicating success
    """
    try:
        reminders_collection = get_collection(DB_NAME, REMINDERS_COLLECTION)
        if reminders_collection is None:
            return False

        user_obj_id = ObjectId(user_id)
        reminder = {
            'user_id': user_obj_id,
            'title': title,
            'datetime': reminder_datetime,
            'notes': notes,
            'created_at': datetime.now(),
            'is_completed': False
        }

        result = reminders_collection.insert_one(reminder)
        return bool(result.inserted_id)
    except Exception as e:
        st.error(f"Error creating reminder: {str(e)}")
        return False


def get_user_reminders(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all reminders for a specific user.

    Args:
        user_id: User ID string

    Returns:
        List of reminder documents
    """
    try:
        reminders_collection = get_collection(DB_NAME, REMINDERS_COLLECTION)
        if reminders_collection is None:
            return []

        user_obj_id = ObjectId(user_id)
        reminder_docs = list(reminders_collection.find({"user_id": user_obj_id}))
        return reminder_docs
    except Exception as e:
        st.error(f"Error loading reminders: {str(e)}")
        return []


def update_reminder_status(reminder_id: ObjectId, is_completed: bool) -> bool:
    """
    Update a reminder's completion status.

    Args:
        reminder_id: Reminder ObjectId
        is_completed: New completion status

    Returns:
        Boolean indicating success
    """
    try:
        reminders_collection = get_collection(DB_NAME, REMINDERS_COLLECTION)
        if reminders_collection is None:
            return False

        result = reminders_collection.update_one(
            {"_id": reminder_id},
            {"$set": {"is_completed": is_completed}}
        )
        return result.modified_count > 0
    except Exception as e:
        st.error(f"Error updating reminder: {str(e)}")
        return False


def delete_reminder(reminder_id: ObjectId) -> bool:
    """
    Delete a reminder from the database.

    Args:
        reminder_id: Reminder ObjectId

    Returns:
        Boolean indicating success
    """
    try:
        reminders_collection = get_collection(DB_NAME, REMINDERS_COLLECTION)
        if reminders_collection is None:
            return False

        result = reminders_collection.delete_one({"_id": reminder_id})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error deleting reminder: {str(e)}")
        return False


def display_reminder_form():
    """
    Display the form for creating a new reminder.

    Returns:
        None
    """
    st.header("Set New Reminder")

    # Title input
    reminder_title = st.text_input("Reminder Title", "My Workout")

    # Date and time inputs
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_date = st.date_input(
            "Select date",
            min_value=datetime.today(),
            max_value=datetime.today() + timedelta(days=MAX_DAYS_IN_FUTURE)
        )
    with col2:
        time_str = st.text_input("Enter time (HH:MM)", DEFAULT_TIME)
        is_valid, selected_time, error_msg = parse_time_input(time_str)
        if not is_valid:
            st.error(error_msg)
            selected_time = datetime.strptime(DEFAULT_TIME, "%H:%M").time()

    # Notes for the reminder
    reminder_notes = st.text_area("Notes (optional)", height=100)

    if st.button("Set Reminder", type="primary"):
        # Create reminder object
        reminder_datetime = datetime.combine(selected_date, selected_time)

        # Get user ID
        user_id = str(st.session_state.user.get('_id'))

        # Create the reminder
        success = create_reminder(user_id, reminder_title, reminder_datetime, reminder_notes)

        if success:
            st.success(
                f"Reminder set successfully for "
                f"{selected_date.strftime('%B %d, %Y')} at {selected_time.strftime('%I:%M %p')}!"
            )
            # Reload page after creating a reminder
            st.rerun()
        else:
            st.error("Failed to create reminder. Please try again.")


def display_user_reminders(user_id: str):
    """
    Display a user's reminders.

    Args:
        user_id: User ID string

    Returns:
        None
    """
    reminder_docs = get_user_reminders(user_id)

    # Display existing reminders
    if reminder_docs:
        st.header("Your Reminders")

        for idx, reminder in enumerate(reminder_docs):
            reminder_title = reminder.get('title', 'Reminder')
            reminder_notes = reminder.get('notes', '')
            reminder_id = reminder.get('_id')
            is_completed = reminder.get('is_completed', False)

            try:
                dt = reminder.get('datetime')
                date_str = dt.strftime('%B %d, %Y at %I:%M %p') if dt else "Unknown date"
            except Exception:
                date_str = "Unknown date"

            # Create the expander title
            if is_completed:
                expander_title = f"✅ {reminder_title} - {date_str}"
            else:
                expander_title = f"🔔 {reminder_title} - {date_str}"

            with st.expander(expander_title):
                if reminder_notes:
                    st.write(f"**Notes:** {reminder_notes}")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if not is_completed:
                        if st.button("Mark Completed", key=f"complete_{idx}"):
                            if update_reminder_status(reminder_id, True):
                                st.rerun()
                    else:
                        if st.button("Mark Incomplete", key=f"incomplete_{idx}"):
                            if update_reminder_status(reminder_id, False):
                                st.rerun()
                with col2:
                    if st.button("Delete", key=f"del_{idx}", type="secondary"):
                        if delete_reminder(reminder_id):
                            st.rerun()
    else:
        st.info("You haven't set any reminders yet.")


@auth_required
def reminder_page():
    """
    Main function to display the reminder management page.

    This page allows users to create new workout reminders
    and manage their existing reminders.
    """
    # Page config
    st.set_page_config(page_title="Workout Reminders", page_icon="📅", layout="centered")
    inject_custom_styles()

    # Ensure user is logged in
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning("Please log in to use the reminder feature.")
        st.stop()

    # Get user ID from session
    user_id = str(st.session_state.user.get('_id'))

    st.title("📅 Workout Reminders")

    # Display form for creating new reminders
    display_reminder_form()

    # Display existing reminders
    display_user_reminders(user_id)


# Run the page
reminder_page()
