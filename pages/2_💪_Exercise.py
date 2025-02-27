import random
from datetime import datetime, timezone, timedelta
import streamlit as st
from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection, get_active_workout_plan, save_workout_log, estimate_calories_burned
from bson.objectid import ObjectId


def get_random_motivational_quote():
    """Return a random motivational fitness quote"""
    quotes = [
        "The only bad workout is the one that didn't happen.",
        "Your body can stand almost anything. It's your mind that you have to convince.",
        "The pain you feel today will be the strength you feel tomorrow.",
        "Don't stop when you're tired. Stop when you're done.",
        "Fitness is not about being better than someone else. It's about being better than you used to be.",
        "The hard days are the best because that's when champions are made.",
        "Success isn't always about greatness. It's about consistency.",
        "The difference between try and triumph is just a little umph!",
        "The only place where success comes before work is in the dictionary.",
        "You don't have to be great to start, but you have to start to be great."
    ]
    return random.choice(quotes)


def get_date_from_key(date_key):
    """Convert a date key from the database format to a datetime object"""
    try:
        return datetime.strptime(date_key, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_for_display(date):
    """Format a date for display in the UI"""
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return date
    return date.strftime("%a, %b %d")


def get_day_number(date_str, plan):
    """Get the day number (1-7) for a given date in the plan"""
    if 'metadata' not in plan or 'start_date' not in plan['metadata']:
        return None

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_date = datetime.fromisoformat(plan['metadata']['start_date']).date()
        days_diff = (date - start_date).days

        if 0 <= days_diff < 7:
            return days_diff + 1
        return None
    except (ValueError, TypeError):
        return None


def is_workout_completed_today(user_id, workout_date):
    """Check if the user has already logged a workout for the given date"""
    collection = get_collection("fitlistic", "workout_logs")
    if collection is None:
        return False

    # Parse the workout date
    workout_date_obj = datetime.strptime(workout_date, "%Y-%m-%d").date()

    # Create date range in UTC
    day_start = datetime.combine(workout_date_obj, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(workout_date_obj, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Find any workout logs for this date
    workout_log = collection.find_one({
        "user_id": ObjectId(user_id),
        "date": {"$gte": day_start, "$lte": day_end}
    })

    return workout_log is not None


def get_next_workout_day(workout_plan, current_date_str):
    """Find the next day with a workout after the given date"""
    if not workout_plan or 'schedule' not in workout_plan:
        return None

    try:
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    # Sort the dates in the schedule
    date_keys = sorted(workout_plan['schedule'].keys())

    # Find the current date index
    current_idx = None
    for i, date_key in enumerate(date_keys):
        date = get_date_from_key(date_key)
        if date and date >= current_date:
            current_idx = i
            break

    # If we didn't find a match or it's the last day, return None
    if current_idx is None or current_idx >= len(date_keys) - 1:
        return None

    # Find the next workout day that isn't a rest day
    for i in range(current_idx + 1, len(date_keys)):
        date_key = date_keys[i]
        if workout_plan['schedule'][date_key]['type'] != 'Rest Day':
            return date_key

    return None


def check_new_plan(user_id):
    """Check if a new plan was just created"""
    # Look for a query parameter indicating a new plan was created
    if st.query_params.get("new_plan") == "true":
        # Reset to the first day of the plan
        active_plan = get_active_workout_plan(user_id)
        if active_plan and 'schedule' in active_plan:
            date_keys = sorted(active_plan['schedule'].keys())
            if date_keys:
                st.session_state.viewed_date = date_keys[0]

        # Clear the query parameter to avoid repeated resets
        st.query_params["new_plan"] = ""
        return True
    return False


@auth_required
def exercise_page():
    st.set_page_config(page_title="Exercise", page_icon="💪", layout="centered")
    inject_custom_styles()

    st.title("💪 Your Workout")

    user_id = str(st.session_state.user.get('_id'))
    active_plan = get_active_workout_plan(user_id)

    if active_plan is None:
        st.info("No active workout plan found. Generate a plan with the Workout Creator")
        if st.button("Go to Workout Creator"):
            st.switch_page("pages/5_📋_Workout-Creator.py")
        return

    # Check if a new plan was just created
    is_new_plan = check_new_plan(user_id)

    # Get today's date
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")

    # Initialize the viewed date
    if "viewed_date" not in st.session_state or is_new_plan:
        # For new plans, use the first date; otherwise, try to find today in the plan
        if is_new_plan:
            date_keys = sorted(active_plan['schedule'].keys())
            st.session_state.viewed_date = date_keys[0] if date_keys else today_str
        else:
            # Check if today is in the plan
            if today_str in active_plan['schedule']:
                st.session_state.viewed_date = today_str
            else:
                # Find the closest date in the plan
                date_keys = sorted(active_plan['schedule'].keys())
                closest_date = min(date_keys, key=lambda x: abs(
                    (get_date_from_key(x) or today) - today)) if date_keys else today_str
                st.session_state.viewed_date = closest_date

    # Check if a specific date was requested via query parameter
    if "date" in st.query_params and not is_new_plan:
        requested_date = st.query_params.get("date")
        if requested_date in active_plan['schedule']:
            st.session_state.viewed_date = requested_date

    # Get workout for the viewed date
    current_date = st.session_state.viewed_date

    # Create date objects for display
    start_date = None
    if 'metadata' in active_plan and 'start_date' in active_plan['metadata']:
        start_date = datetime.fromisoformat(active_plan['metadata']['start_date']).date()

    # Add date navigation
    if start_date:
        st.write("**Navigate Days:**")
        date_keys = sorted(active_plan['schedule'].keys())

        # Create a row of small buttons for day navigation
        cols = st.columns(7)
        for i, date_key in enumerate(date_keys):
            day_num = i + 1

            with cols[i]:
                day_label = f"Day {day_num}"

                # Highlight the current day
                if date_key == current_date:
                    st.markdown(f"**[{day_label}]**")
                else:
                    if st.button(day_label, key=f"day_{date_key}", use_container_width=True):
                        st.session_state.viewed_date = date_key
                        st.query_params["date"] = date_key
                        st.rerun()

    current_workout = active_plan['schedule'].get(current_date)

    if current_workout is None:
        st.error(f"No workout found for {format_date_for_display(current_date)}.")
        return

    if current_workout is None:
        st.error(f"No workout found for {format_date_for_display(current_date)}.")
        return

    # Get the day number for display
    day_number = get_day_number(current_date, active_plan)
    day_display = f"Day {day_number}" if day_number else "Workout"

    if current_workout['type'] == 'Rest Day':
        st.header(f"Day {day_number} ({format_date_for_display(current_date)})")
        st.markdown("""
        ### 🌟 Time to Recharge! 

        Today is your well-deserved rest day! Remember:
        - 😴 Rest is when your body gets stronger
        - 🧘‍♀️ Light stretching and walks are a perfect way to optimize recovery
        - 🎮 Enjoy some guilt-free relaxation
        - 🥗 Focus on good nutrition and hydration
        """)

        # Find the next workout day
        next_day = get_next_workout_day(active_plan, current_date)
        if next_day:
            next_day_num = get_day_number(next_day, active_plan)
            next_day_label = f"Day {next_day_num}"
            if st.button(f"View {next_day_label}", type="primary"):
                st.session_state.viewed_date = next_day
                st.query_params["date"] = next_day
                st.rerun()
        return

    # Check if this workout is already completed for this date
    is_completed = is_workout_completed_today(user_id, current_date)

    # Display day heading
    st.header(f"Day {day_number} ({format_date_for_display(current_date)})")

    if is_completed:
        # Show completion image and motivational quote
        col1, col2 = st.columns([2, 1])

        with col1:
            st.image("images/Finish.png", width=400)

        with col2:
            st.success("✅ Workout Completed!")
            st.markdown(f"### \"{get_random_motivational_quote()}\"")

        # Offer to show the next day's workout
        next_day = get_next_workout_day(active_plan, current_date)
        if next_day:
            next_day_num = get_day_number(next_day, active_plan)
            next_day_label = f"Day {next_day_num}"
            if st.button(f"View {next_day_label}", type="primary"):
                st.session_state.viewed_date = next_day
                st.query_params["date"] = next_day
                st.rerun()
        else:
            st.info("You've completed all scheduled workouts in this plan!")

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
        if st.button("Mark as Complete", type="primary", use_container_width=True):
            workout_date = datetime.strptime(current_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            success, message = save_workout_log(
                user_id,
                current_date,
                current_workout.get('schedule', []),
                current_workout.get('type', 'Daily'),
                workout_notes
            )

            if success:
                st.success("Workout completed! Your progress has been saved.")

                # Offer to show the next day's workout
                next_day = get_next_workout_day(active_plan, current_date)
                if next_day:
                    next_day_num = get_day_number(next_day, active_plan)
                    next_day_label = f"Day {next_day_num}"
                    if st.button(f"View {next_day_label}"):
                        st.session_state.viewed_date = next_day
                        st.query_params["date"] = next_day
                        st.rerun()
                else:
                    st.success("You've completed all scheduled workouts in this plan!")

            else:
                st.error(f"Failed to log workout: {message}")

    with col2:
        # If viewing a day other than today, offer to return to today
        if current_date != today_str:
            if today_str in active_plan['schedule']:
                if st.button(f"Go to Today's Workout", use_container_width=True):
                    st.session_state.viewed_date = today_str
                    st.query_params["date"] = today_str
                    st.rerun()
            else:
                if st.button("Create New Workout Plan", use_container_width=True):
                    st.switch_page("pages/5_📋_Workout-Creator.py")
        else:
            if st.button("Create New Workout Plan", use_container_width=True):
                st.switch_page("pages/5_📋_Workout-Creator.py")


def display_workout_details(workout, user_id):
    """Display the details of a workout"""
    # Handle both old structure (workout_refs) and new structure (schedule)
    workout_items = workout.get('schedule', [])

    # If no schedule found, check for the old workout_refs structure
    if not workout_items and 'workout_refs' in workout:
        # Old format: Use the workout_refs
        workout_refs = workout.get('workout_refs', [])

        # Check if there are exercises to display
        if not workout_refs:
            st.info(
                "No exercises found for this workout day. This may be a rest day or a plan created with an older version.")
            return

        # Get workout references and display them
        # This is a placeholder - you'll need to adjust based on how workout_refs are structured
        st.info("This workout plan was created with an older version. Please create a new plan for full details.")

        # Display what we can from the old structure
        for i, ref in enumerate(workout_refs, 1):
            st.write(f"{i}. Activity duration: {ref.get('duration', 'N/A')} minutes")

        return

    # Show estimated calories and duration for the new structure
    total_duration = sum(block.get('duration', 0) for block in workout_items)
    user_weight = st.session_state.user.get('weight', 70)

    # Estimate calories for each activity type
    total_calories = 0
    for block in workout_items:
        activity_type = block.get('activity', {}).get('type', 'unknown')
        duration = block.get('duration', 0)
        total_calories += estimate_calories_burned(activity_type, duration, user_weight)

    # Display summary metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Duration", f"{total_duration} min")
    with col2:
        st.metric("Estimated Calories", f"{total_calories} kcal")

    # Check if there are activities to display
    if not workout_items:
        st.info("No activities found for this workout day.")
        return

    # Display exercises
    for i, block in enumerate(workout_items, 1):
        activity = block.get('activity', {})
        if not activity:
            continue

        activity_name = activity.get('name', 'Unnamed Activity')
        duration = block.get('duration', 'N/A')

        with st.expander(f"{i}. {activity_name} ({duration} min)"):
            activity_type = activity.get('type', '')

            # Show equipment and target heart rate for warm-ups and cool-downs
            if activity_type in ["warm_up", "cool_down"]:
                equipment = activity.get("equipment_needed", "None")
                if isinstance(equipment, list) and equipment:
                    st.markdown(f"**Equipment needed:** {', '.join(equipment)}")
                elif isinstance(equipment, str) and equipment:
                    st.markdown(f"**Equipment needed:** {equipment}")

                target_hr = activity.get("target_heart_rate", "")
                if target_hr:
                    st.markdown(f"**Target heart rate:** {target_hr}")

            # Display phases for warm-ups and cool-downs
            phases = activity.get("phases", [])
            if phases and isinstance(phases, list):
                for phase in phases:
                    if isinstance(phase, dict):
                        st.markdown(f"### {phase.get('name', 'Unnamed Phase')}")

                        # Display exercises in this phase
                        phase_exercises = phase.get("exercises", [])
                        if phase_exercises and isinstance(phase_exercises, list):
                            for ex in phase_exercises:
                                if isinstance(ex, dict):
                                    st.markdown(f"**{ex.get('name', 'Unnamed Exercise')}**")

                                    # Display reps if available
                                    reps = ex.get('reps', '')
                                    if reps:
                                        st.markdown(f"Reps: {reps}")

                                    # Display exercise instructions
                                    ex_instructions = ex.get('instructions', [])
                                    if ex_instructions:
                                        st.markdown("Instructions:")
                                        for instruction in ex_instructions:
                                            st.markdown(f"- {instruction}")

                                    st.markdown("---")

            # Handle stretching routines with sequences
            sequence = activity.get("sequence", [])
            if sequence and isinstance(sequence, list):
                for exercise in sequence:
                    if isinstance(exercise, dict):
                        st.markdown(f"**{exercise.get('name', 'Unnamed Exercise')}**")
                        if 'reps' in exercise:
                            st.markdown(f"Reps: {exercise['reps']}")

                        instructions = exercise.get('instructions', [])
                        if instructions:
                            st.markdown("Instructions:")
                            for instruction in instructions:
                                st.markdown(f"- {instruction}")

                        st.markdown("---")

            # Handle breathwork with steps
            steps = activity.get("steps", [])
            # Only display steps if they are strings, not dictionaries
            if steps and isinstance(steps, list) and all(isinstance(step, str) for step in steps):
                st.markdown("**Steps:**")
                for step in steps:
                    st.markdown(f"- {step}")
            elif steps and isinstance(steps, str):
                st.markdown("**Steps:**")
                for step in steps.split('\n'):
                    st.markdown(f"- {step}")

            # Handle meditation with steps - display in nicely formatted way only
            meditation_steps = activity.get("steps", [])
            if meditation_steps and isinstance(meditation_steps, list) and all(
                    isinstance(step, dict) for step in meditation_steps):
                for step in meditation_steps:
                    st.markdown(f"**Phase: {step.get('phase', 'Unknown phase')}**")

                    instructions = step.get('instructions', [])
                    if instructions:
                        st.markdown("Instructions:")
                        for instruction in instructions:
                            st.markdown(f"- {instruction}")
                    st.markdown("---")

            # Handle regular exercises
            exercises = activity.get("exercises", [])
            if exercises and isinstance(exercises, list) and activity_type == "exercise":
                for ex in exercises:
                    if isinstance(ex, dict):
                        st.markdown(f"**{ex.get('name', 'Unnamed Exercise')}**")

                        form_cues = ex.get('form_cues', [])
                        if form_cues:
                            st.markdown("Form cues:")
                            for cue in form_cues:
                                st.markdown(f"- {cue}")

                        sets = ex.get("sets", "N/A")
                        reps = ex.get("reps", "N/A")
                        st.markdown(f"Sets: {sets} | Reps: {reps}")

            # Handle any instructions
            instructions = activity.get("instructions", [])
            if instructions and isinstance(instructions, list):
                st.markdown("Instructions:")
                for instruction in instructions:
                    st.markdown(f"- {instruction}")

            # Show benefits if available
            benefits = activity.get("benefits", [])
            if benefits and isinstance(benefits, list):
                st.markdown("\n**Benefits:**")
                for benefit in benefits:
                    st.markdown(f"- {benefit}")

            # Hide target areas for stretching routines but keep for other activities
            if activity_type != "stretching":
                target_areas = activity.get("target_areas", [])
                if target_areas and isinstance(target_areas, list):
                    st.markdown(f"\n**Target Areas:** {', '.join(target_areas)}")


exercise_page()
