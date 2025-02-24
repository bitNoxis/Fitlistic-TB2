from datetime import datetime, timezone
import streamlit as st
from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection, get_active_workout_plan, save_workout_log, estimate_calories_burned
from bson.objectid import ObjectId


def is_workout_completed_today(user_id, workout_type):
    """Check if the user has already logged this workout type today"""
    collection = get_collection("fitlistic", "workout_logs")
    if collection is None:
        return False

    # Get today's date range in UTC
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Find any workout logs matching the workout type for today
    workout_log = collection.find_one({
        "user_id": ObjectId(user_id),
        "date": {"$gte": today_start, "$lte": today_end},
        "workout_notes": {"$regex": f"Completed {workout_type}", "$options": "i"}
    })

    return workout_log is not None


def get_next_day(current_day):
    """Get the next day of the week"""
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    current_index = days.index(current_day.lower())
    next_index = (current_index + 1) % 7
    return days[next_index]


def get_next_workout_day(workout_plan, start_day):
    """Find the next day with a workout after the given day"""
    if not workout_plan:
        return None

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    start_index = days.index(start_day.lower())

    # Check all days starting after the given day
    for i in range(1, 8):
        check_index = (start_index + i) % 7
        check_day = days[check_index]

        if check_day in workout_plan['schedule'] and workout_plan['schedule'][check_day][
            'type'] != 'Rest & Rejuvenation':
            return check_day

    return None  # No workout found


def check_new_plan(user_id):
    """Check if a new plan was just created"""
    # Look for a query parameter indicating a new plan was created
    if st.query_params.get("new_plan") == "true":
        # Reset the viewed day to Monday
        st.session_state.viewed_day = "monday"
        # Clear the query parameter to avoid repeated resets
        st.query_params["new_plan"] = ""
        return True
    return False


@auth_required
def exercise_page():
    st.set_page_config(page_title="Exercise", page_icon="💪", layout="centered")
    inject_custom_styles()

    st.title("Your Workout")

    user_id = str(st.session_state.user.get('_id'))
    active_plan = get_active_workout_plan(user_id)

    if active_plan is None:
        st.info("No active workout plan found. Generate a plan with the Workout Creator")
        if st.button("Go to Workout Creator"):
            st.switch_page("pages/5_📋_Workout-Creator.py")
        return

    # Check if a new plan was just created
    is_new_plan = check_new_plan(user_id)

    # Get today's day
    today = datetime.now().strftime("%A").lower()

    # Initialize the viewed day
    if "viewed_day" not in st.session_state or is_new_plan:
        # Default to Monday for new plans, otherwise show today
        st.session_state.viewed_day = "monday" if is_new_plan else today

    # Check if a specific day was requested via query parameter
    if "day" in st.query_params and not is_new_plan:
        requested_day = st.query_params.get("day").lower()
        if requested_day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            st.session_state.viewed_day = requested_day

    # Get workout for the viewed day
    current_day = st.session_state.viewed_day

    # Add day tabs for easy navigation
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    # Create a row of small buttons for day navigation
    st.write("**Navigate Days:**")
    cols = st.columns(7)
    for i, (day, label) in enumerate(zip(days, day_labels)):
        with cols[i]:
            # Highlight the current day
            if day == current_day:
                st.markdown(f"**[{label}]**")
            else:
                if st.button(label, key=f"day_{day}", use_container_width=True):
                    st.session_state.viewed_day = day
                    st.query_params["day"] = day
                    st.rerun()

    current_workout = active_plan['schedule'].get(current_day)

    if current_workout is None or current_workout['type'] == 'Rest & Rejuvenation':
        st.info(f"No workout scheduled for {current_day.capitalize()}. It's a rest day!")

        # Find the next workout day
        next_day = get_next_workout_day(active_plan, current_day)
        if next_day:
            if st.button(f"View {next_day.capitalize()}'s Workout", type="primary"):
                st.session_state.viewed_day = next_day
                st.query_params["day"] = next_day
                st.rerun()
        return

    # Check if this workout is already completed today
    is_completed = is_workout_completed_today(user_id, current_workout['type'])

    # Display day and workout type
    st.header(f"{current_day.capitalize()}: {current_workout['type']}")

    if is_completed:
        st.success("✅ You've already completed this workout today!")

        # Offer to show the next day's workout
        next_day = get_next_workout_day(active_plan, current_day)
        if next_day:
            if st.button(f"View {next_day.capitalize()}'s Workout", type="primary"):
                st.session_state.viewed_day = next_day
                st.query_params["day"] = next_day
                st.rerun()
        else:
            st.info("You've completed all scheduled workouts this week!")

        # Option to view details even if completed
        if st.button("Show Workout Details", type="secondary"):
            display_workout_details(current_workout, user_id)

        return

    # Display workout details and completion options for incomplete workouts
    display_workout_details(current_workout, user_id)

    # Completion section
    st.markdown("---")
    st.subheader("Complete Your Workout")

    workout_notes = st.text_area("How did this workout feel?", placeholder="Add any notes about today's workout...")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Mark as Complete", type="primary", use_container_width=True):
            success, message = save_workout_log(
                user_id,
                current_workout.get('workout_refs', []),
                current_workout.get('type', 'Daily'),
                workout_notes
            )

            if success:
                st.success("Workout completed! Your progress has been saved.")

                # Offer to show the next day's workout
                next_day = get_next_workout_day(active_plan, current_day)
                if next_day:
                    if st.button(f"View {next_day.capitalize()}'s Workout"):
                        st.session_state.viewed_day = next_day
                        st.query_params["day"] = next_day
                        st.rerun()
                else:
                    st.success("You've completed all scheduled workouts this week!")

                if st.button("Return to Home"):
                    st.switch_page("pages/1_🏠_Overview.py")
            else:
                st.error(f"Failed to log workout: {message}")

    with col2:
        # If viewing a day other than today, offer to return to today
        if current_day != today:
            if st.button(f"Go to Today's Workout", use_container_width=True):
                st.session_state.viewed_day = today
                st.query_params["day"] = today
                st.rerun()
        else:
            if st.button("Create New Workout Plan", use_container_width=True):
                st.switch_page("pages/5_📋_Workout-Creator.py")


def display_workout_details(workout, user_id):
    """Display the details of a workout"""
    # Show estimated calories and duration
    total_duration = sum(ref.get('duration', 0) for ref in workout.get('workout_refs', []))
    user_weight = st.session_state.user.get('weight', 70)

    total_calories = sum(
        estimate_calories_burned(ref.get('activity_type', 'unknown'), ref.get('duration', 0), user_weight)
        for ref in workout.get('workout_refs', [])
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Duration", f"{total_duration} min")
    with col2:
        st.metric("Estimated Calories", f"{total_calories} kcal")

    # Display exercises
    for i, workout_ref in enumerate(workout.get('workout_refs', []), 1):
        exercise = workout_ref.get('exercise_details', {})
        if not exercise:
            continue

        with st.expander(f"{i}. {exercise['name']} ({workout_ref['duration']} min)"):
            if 'sequence' in exercise:
                for seq in exercise['sequence']:
                    st.markdown(f"**{seq['name']}**")
                    st.markdown(f"Duration: {seq['duration']}")
                    st.markdown(f"Reps: {seq['reps']}")
                    for instruction in seq.get('instructions', []):
                        st.markdown(f"- {instruction}")
                    st.markdown("---")

            elif 'steps' in exercise:
                for step in exercise['steps']:
                    if isinstance(step, dict):
                        st.markdown(f"**{step.get('phase', '')}**")
                        st.markdown(f"Duration: {step.get('duration_minutes', '')} minutes")
                        for instruction in step.get('instructions', []):
                            st.markdown(f"- {instruction}")
                    else:
                        st.markdown(f"- {step}")

            elif 'form_cues' in exercise:
                st.markdown("**Form Cues:**")
                for cue in exercise['form_cues']:
                    st.markdown(f"- {cue}")

                if 'difficulty_levels' in exercise:
                    level = st.session_state.user.get('level', 'beginner')
                    level_info = exercise.get('difficulty_levels', {}).get(level, {})
                    if level_info:
                        st.markdown(f"**{level.capitalize()} Level:**")
                        st.markdown(f"Sets: {level_info.get('sets', 'N/A')}")
                        st.markdown(f"Reps: {level_info.get('reps', 'N/A')}")
                        st.markdown(f"Rest: {level_info.get('rest', 'N/A')} seconds")
                        if 'tempo' in level_info:
                            st.markdown(f"Tempo: {level_info['tempo']}")

            if 'benefits' in exercise:
                st.markdown("\n**Benefits:**")
                for benefit in exercise['benefits']:
                    st.markdown(f"- {benefit}")

            if 'target_areas' in exercise:
                st.markdown(f"\n**Target Areas:** {', '.join(exercise['target_areas'])}")

            if 'muscle_groups' in exercise:
                st.markdown(f"\n**Muscle Groups:** {', '.join(exercise['muscle_groups'])}")


exercise_page()
