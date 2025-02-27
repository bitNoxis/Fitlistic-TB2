import streamlit as st
from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection
from bson.objectid import ObjectId
import json


@auth_required
def profile_page():
    st.set_page_config(page_title="Profile | Fitlistic", page_icon="👤", layout="centered")
    inject_custom_styles()

    with st.sidebar:
        st.header(f"Quick Options")
        handle_sidebar_buttons()

    # Get user from session state
    if "user" not in st.session_state:
        st.error("You must be logged in to view this page")
        return

    user = st.session_state.user
    user_id = user.get("_id")

    st.title("👤 Edit your Profile")

    # Logout button below title but above tabs
    if st.button("Log Out", type="primary"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("You have been logged out successfully.")
        st.rerun()

    # Container for the main content
    with st.container():
        # Create tabs for different sections
        tab1, tab2 = st.tabs(["Profile Info", "Account Settings"])

        # Tab 1: Profile Info
        with tab1:
            # Removed the columns since we're not using profile picture

            # Basic user info
            st.subheader(f"{user.get('first_name', '')} {user.get('last_name', '')}")
            st.write(f"**Username:** {user.get('username', '')}")
            st.write(f"**Email:** {user.get('email', '')}")

            # Account age - with timezone-aware comparison
            if user.get("created_at"):
                try:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    created_at = user.get("created_at")

                    # Ensure created_at has timezone info
                    if created_at.tzinfo is None:
                        import pytz
                        created_at = pytz.utc.localize(created_at)

                    days = (now - created_at).days
                    st.write(f"**Member for:** {days} days")
                except Exception as e:
                    st.write("**Member since:** {0:%B %d, %Y}".format(created_at))

            # Physical stats section with edit functionality
            st.subheader("Physical Stats & Fitness Goals")

            # Physical stats
            col1, col2 = st.columns(2)
            with col1:
                current_height = user.get("height", 0)
                new_height = st.number_input("Height (cm)", min_value=0, max_value=300, value=current_height, step=1)

            with col2:
                current_weight = user.get("weight", 0)
                new_weight = st.number_input("Weight (kg)", min_value=0, max_value=500, value=current_weight, step=1)

            # Fitness goals
            st.write("**Your Fitness Goals:**")
            # List of available goals
            available_goals = [
                "Flexibility",
                "Better Mental Health",
                "Stress Resilience",
                "General Fitness",
                "Weight Loss",
                "Muscle Gain"
            ]

            # Get current goals
            current_goals = user.get("fitness_goals", [])

            # Display as multiselect
            selected_goals = st.multiselect(
                "Select your fitness goals",
                available_goals,
                default=current_goals,
                key="fitness_goals"
            )

            # Save changes button for both stats and goals
            if ((new_height != current_height or new_weight != current_weight or
                 set(selected_goals) != set(current_goals)) and
                    st.button("Update Stats & Goals")):

                update_data = {
                    "height": new_height,
                    "weight": new_weight,
                    "fitness_goals": selected_goals
                }

                update_profile_data(user_id, update_data)
                st.success("Profile information updated successfully!")

                # Update session state completely
                # First, get the latest user data from DB to ensure we have all fields
                collection = get_collection("fitlistic", "users")
                updated_user = collection.find_one({"_id": ObjectId(user_id)})

                if updated_user:
                    # Convert ObjectId to string for session state compatibility
                    updated_user["_id"] = str(updated_user["_id"])
                    # Update the entire session state user
                    st.session_state.user = updated_user
                else:
                    # If for some reason we can't get the updated user, at least update the fields we know
                    st.session_state.user["height"] = new_height
                    st.session_state.user["weight"] = new_weight
                    st.session_state.user["fitness_goals"] = selected_goals

                st.rerun()

        # Tab 2: Account Settings
        with tab2:
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
                        # Update session state completely by fetching fresh user data
                        collection = get_collection("fitlistic", "users")
                        updated_user = collection.find_one({"_id": ObjectId(user_id)})

                        if updated_user:
                            # Convert ObjectId to string for session state compatibility
                            updated_user["_id"] = str(updated_user["_id"])
                            # Update the entire session state user
                            st.session_state.user = updated_user
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
                            # Get the latest user data from DB to ensure we have all fields
                            collection = get_collection("fitlistic", "users")
                            updated_user = collection.find_one({"_id": ObjectId(user_id)})

                            if updated_user:
                                # Convert ObjectId to string for session state compatibility
                                updated_user["_id"] = str(updated_user["_id"])
                                # Update the entire session state user
                                st.session_state.user = updated_user

                            st.success("Password updated successfully!")
                        else:
                            st.error("Current password is incorrect or there was an error updating your password.")

            # Logout button was moved to the top of the page


def handle_sidebar_buttons():
    if st.button("Log Out"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("You have been logged out successfully.")
    if st.button("Create New Account"):
        st.switch_page("pages/_Register.py")


def update_profile_data(user_id, update_data):
    """Update user profile data in MongoDB"""
    try:
        collection = get_collection("fitlistic", "users")
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


def verify_and_update_password(user_id, current_password, new_password):
    """Verify current password and update to new password if correct"""
    from utils.mongo_helper import verify_password, hash_password

    try:
        collection = get_collection("fitlistic", "users")
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


profile_page()
