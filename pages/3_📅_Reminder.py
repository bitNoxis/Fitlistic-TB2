import streamlit as st
from datetime import datetime, timedelta
from bson import ObjectId

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection


@auth_required
def reminder_page():
    # Page config
    st.set_page_config(page_title="Reminder", page_icon="📅", layout="centered")
    inject_custom_styles()

    # Get user info from session state
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning("Please log in to use the reminder feature.")
        st.stop()

    # Get user ID from session
    user_id = str(st.session_state.user.get('_id'))

    # Get reminders collection
    reminders_collection = get_collection("fitlistic", "reminders")

    # Initialize reminders list in session state
    if 'reminders' not in st.session_state:
        st.session_state.reminders = []

    st.title("📅 Workout Reminders")

    # Create a simple reminder interface
    st.header("Set New Reminder")

    reminder_title = st.text_input("Reminder Title", "My Workout")

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_date = st.date_input(
            "Select date",
            min_value=datetime.today(),
            max_value=datetime.today() + timedelta(days=365)
        )
    with col2:
        # Free-form time input instead of picker
        time_str = st.text_input("Enter time (HH:MM)", "08:00")

        # Parse the entered time
        try:
            hour, minute = map(int, time_str.split(':'))
            if 0 <= hour < 24 and 0 <= minute < 60:
                selected_time = datetime.strptime(time_str, "%H:%M").time()
            else:
                st.error("Invalid time format. Please use HH:MM (24-hour format).")
                selected_time = datetime.strptime("00:00", "%H:%M").time()
        except ValueError:
            st.error("Invalid time format. Please use HH:MM (24-hour format).")
            selected_time = datetime.strptime("00:00", "%H:%M").time()

    # Notes for the reminder
    reminder_notes = st.text_area("Notes (optional)", height=100)

    if st.button("Set Reminder", type="primary"):
        # Create reminder object
        reminder_datetime = datetime.combine(selected_date, selected_time)

        # Convert user_id to ObjectId
        user_obj_id = ObjectId(user_id)

        reminder = {
            'user_id': user_obj_id,
            'title': reminder_title,
            'datetime': reminder_datetime,
            'notes': reminder_notes,
            'created_at': datetime.now(),
            'is_completed': False
        }

        # Save to MongoDB
        reminders_collection.insert_one(reminder)

        st.success(
            f"Reminder set successfully for "
            f"{selected_date.strftime('%B %d, %Y')} at {selected_time.strftime('%I:%M %p')}!"
        )

        # Reload page after creating a reminder
        st.rerun()

    # Load the latest reminders directly from the database each time
    try:
        user_obj_id = ObjectId(user_id)
        reminder_docs = list(reminders_collection.find({"user_id": user_obj_id}))

        # Display existing reminders
        if reminder_docs:
            st.header("Your Reminders")

            for idx, reminder in enumerate(reminder_docs):
                reminder_title = reminder.get('title', 'Reminder')
                reminder_notes = reminder.get('notes', '')
                is_completed = reminder.get('is_completed', False)

                try:
                    dt = reminder.get('datetime')
                    date_str = dt.strftime('%B %d, %Y at %I:%M %p') if dt else "Unknown date"
                except:
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
                                reminder_id = reminder['_id']
                                reminders_collection.update_one(
                                    {"_id": reminder_id},
                                    {"$set": {"is_completed": True}}
                                )
                                st.rerun()
                    with col2:
                        if st.button("Delete", key=f"del_{idx}"):
                            reminder_id = reminder['_id']
                            reminders_collection.delete_one({"_id": reminder_id})
                            st.rerun()
        else:
            st.info("You haven't set any reminders yet.")
    except Exception as e:
        st.error(f"Error loading reminders: {str(e)}")


# Run the page
reminder_page()
