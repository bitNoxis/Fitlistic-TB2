import streamlit as st
from datetime import datetime, timedelta
from utils.auth_helper import auth_required


@auth_required
def reminder_page():
    # Page config
    st.set_page_config(page_title="Reminder", page_icon="📅", layout="centered")

    # Initialize reminders if needed
    if 'reminders' not in st.session_state:
        st.session_state.reminders = []

    st.title("Workout Reminders")

    # Add new reminder
    st.header("Set New Reminder")

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_date = st.date_input(
            "Select date",
            min_value=datetime.today(),
            max_value=datetime.today() + timedelta(days=365)
        )
    with col2:
        selected_time = st.time_input("Select time")

    workout_type = st.selectbox(
        "Workout Type",
        ["Fullbody Workout", "Upperbody Workout", "Power Recovery", "Lower Body"]
    )

    if st.button("Set Reminder", type="primary"):
        reminder = {
            'date': selected_date,
            'time': selected_time,
            'workout': workout_type
        }
        st.session_state.reminders.append(reminder)
        st.success("Reminder set successfully!")

    # Display existing reminders
    if st.session_state.reminders:
        st.header("Your Reminders")

        for idx, reminder in enumerate(st.session_state.reminders):
            with st.expander(
                    f"Reminder for {reminder['date'].strftime('%B %d, %Y')} "
                    f"at {reminder['time'].strftime('%I:%M %p')}"
            ):
                st.write(f"Workout: {reminder['workout']}")
                if st.button("Delete Reminder", key=f"del_{idx}"):
                    st.session_state.reminders.pop(idx)
                    st.rerun()
    else:
        st.info("You haven't set any reminders yet.")


# Run the page
reminder_page()
