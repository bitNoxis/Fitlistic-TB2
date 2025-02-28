"""
Workout Creator Module

This module provides functionality to generate personalized 7-day holistic workout plans
based on user preferences, fitness goals, and experience level.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import streamlit as st

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.holistic_planner import generate_weekly_plan
from utils.mongo_helper import get_collection, save_workout_plan

# Constants
EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]
WORKOUT_DURATIONS = [15, 30, 45, 60]
DEFAULT_DURATION_INDEX = 1  # 30 minutes (index 1 in WORKOUT_DURATIONS)
DEFAULT_REST_DAY = 6  # Default to Day 7
MAX_PLAN_DAYS = 30
DEFAULT_WEIGHT = 70
DEFAULT_HEIGHT = 170
DEFAULT_GOAL = "General Fitness"


def get_date_range(start_date: datetime.date, days: int = 7) -> List[datetime.date]:
    """
    Generate a list of dates starting from the given date.

    Args:
        start_date: Starting date for the range
        days: Number of days to include

    Returns:
        List of date objects
    """
    return [(start_date + timedelta(days=i)) for i in range(days)]


def format_date_for_display(date: datetime.date) -> str:
    """
    Format a date for display in the UI.

    Args:
        date: Date to format

    Returns:
        Formatted date string (e.g., "Mon, Jan 15")
    """
    return date.strftime("%a, %b %d")


def format_date_for_db(date: datetime.date) -> str:
    """
    Format a date for storage in the database.

    Args:
        date: Date to format

    Returns:
        Formatted date string (e.g., "2023-01-15")
    """
    return date.strftime("%Y-%m-%d")


def format_time(time_str: str) -> str:
    """
    Format a time string from 24-hour to 12-hour format.

    Args:
        time_str: Time string in HH:MM format

    Returns:
        Formatted time string with AM/PM
    """
    return datetime.strptime(time_str, '%H:%M').strftime('%I:%M %p')


def initialize_collections() -> Dict[str, Any]:
    """
    Initialize required database collections.

    Returns:
        Dictionary of collection objects
    """
    collections = {
        "exercises": get_collection("fitlistic", "exercises"),
        "breathwork": get_collection("fitlistic", "breathwork_techniques"),
        "meditation": get_collection("fitlistic", "meditation_templates"),
        "stretching": get_collection("fitlistic", "stretching_routines"),
        "cool_downs": get_collection("fitlistic", "cool_downs"),
        "warm_ups": get_collection("fitlistic", "warm_ups")
    }

    return collections


def display_rest_day_message() -> None:
    """Display a formatted message for rest days."""
    st.markdown("""
    ### 🌟 Rest Day! Time to Recharge! 

    This is your well-deserved rest day! Remember:
    - 😴 Rest is when your body gets stronger
    - 🧘‍♀️ Light stretching and walks are a perfect way to optimize recovery
    - 🎮 Enjoy some guilt-free relaxation
    - 🥗 Focus on good nutrition and hydration
    """)


def display_day_schedule(schedule: Dict[str, Any], day_name: str) -> None:
    """
    Display the workout schedule for a specific day.

    Args:
        schedule: Day schedule dictionary
        day_name: Name of the day (e.g., "Day 1")
    """
    for block in schedule.get('schedule', []):
        activity = block.get("activity", {})
        if not activity:
            st.markdown("No activity information available for this block.")
            continue

        activity_name = activity.get("name", "Unnamed Activity")
        duration = block.get("duration", "N/A")
        activity_type = activity.get("type", "")

        expander_title = f"{activity_name} ({duration} min)"
        with st.expander(expander_title):
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


def display_weekly_plan(plan: Dict[str, Any]) -> None:
    """
    Display the weekly workout plan.

    Args:
        plan: Generated workout plan dictionary
    """
    # Display summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        # Total workout days instead of exercise count
        active_days = len([day for day in plan['schedule'].values()
                           if day['type'] != 'Rest Day'])
        st.metric("Workout Days", active_days)

    with col2:
        # Total minutes - keep this useful metric
        total_minutes = sum(
            sum(block['duration'] for block in day['schedule'])
            for day in plan['schedule'].values()
        )
        st.metric("Total Minutes", total_minutes)

    with col3:
        # Average minutes per workout day
        if active_days > 0:
            avg_minutes = total_minutes / active_days
            st.metric("Avg. Minutes/Day", round(avg_minutes))
        else:
            st.metric("Avg. Minutes/Day", 0)

    # Add button to create a new plan right after metrics
    if st.button("Create Different Plan", key="new_plan_button"):
        # Clear the existing plan
        del st.session_state.weekly_plan
        st.rerun()

    # Create tabs for each day of the plan
    days = list(plan['schedule'].keys())
    day_labels = [f"Day {i + 1}" for i in range(len(days))]

    tabs = st.tabs(day_labels)

    for i, (day, tab) in enumerate(zip(days, tabs)):
        with tab:
            # Display the date within the tab
            if 'metadata' in plan and 'start_date' in plan['metadata']:
                date = get_date_range(datetime.fromisoformat(plan['metadata']['start_date']).date(), len(days))[i]
                formatted_date = format_date_for_display(date)
                st.subheader(f"Day {i + 1}: {formatted_date}")

            if day in plan['schedule']:
                day_schedule = plan['schedule'][day]
                if day_schedule['type'] == 'Rest Day':
                    display_rest_day_message()
                else:
                    display_day_schedule(day_schedule, f"Day {i + 1}")

    # Save plan button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save & Activate Plan", type="primary", key="save_plan_button"):
            user_id = str(st.session_state.user.get('_id'))
            success, message = save_workout_plan(user_id, plan)

            if success:
                st.success("Workout plan saved successfully!")
                st.success("You can look at the plan at the Exercise page.")
                # Add query parameter to help Exercise page detect the new plan
                st.query_params["new_plan"] = "true"
            else:
                st.error(f"Failed to save plan: {message}")


def get_weekly_plan_tab() -> None:
    """Display the main interface for creating and viewing workout plans."""
    st.title("📋 Workout Creator")
    st.header("Generate your 7-Day Holistic Fitness Plan")

    # If a plan exists in session state, display it first
    if 'weekly_plan' in st.session_state:
        display_weekly_plan(st.session_state.weekly_plan)
        return

    # Get today's date
    today = datetime.now().date()

    # Date selection for plan start
    st.subheader("Select your plan start date")
    start_date = st.date_input(
        "When would you like to start your plan?",
        value=today,
        min_value=today,
        max_value=today + timedelta(days=MAX_PLAN_DAYS),
        key="plan_start_date",
        help="Your plan will begin on this date and continue for 7 days"
    )

    # Create date range for the plan
    date_range = get_date_range(start_date, days=7)
    formatted_dates = [format_date_for_display(date) for date in date_range]
    formatted_db_dates = [format_date_for_db(date) for date in date_range]

    col1, col2 = st.columns(2)

    with col1:
        # Experience Level Selector with multiselect
        experience_level = st.multiselect(
            "Select your experience level(s)",
            options=EXPERIENCE_LEVELS,
            default=[EXPERIENCE_LEVELS[0]],
            key="experience_selector",
            help="This will adjust the intensity and complexity of your workouts"
        )
        # Use the first selected experience level, converting to lowercase for backend processing
        selected_level = experience_level[0].lower() if experience_level else EXPERIENCE_LEVELS[0].lower()

    with col2:
        # Rest day selector with single select dropdown
        day_options = [f"Day {i + 1} ({formatted_dates[i]})" for i in range(7)]
        selected_rest_day_index = st.selectbox(
            "Choose your preferred rest day",
            options=range(len(day_options)),
            format_func=lambda i: day_options[i],
            index=DEFAULT_REST_DAY,
            key="rest_day_selector",
            help="Select the day that best fits your schedule for rest and recovery"
        )
        # Convert to the date string format for storage
        selected_rest_day = formatted_db_dates[selected_rest_day_index]

    # Workout duration selection with options
    workout_duration = st.selectbox(
        "Main duration per Day (minutes)",
        options=WORKOUT_DURATIONS,
        index=DEFAULT_DURATION_INDEX,
        key="workout_duration",
        help="Total daily time for your main exercises"
    )

    # Initialize required collections
    collections = initialize_collections()

    # Check if all collections are available
    if any(coll is None for coll in collections.values()):
        st.error("Failed to connect to one or more required collections")
        return

    # Generate button - only generate when clicked, don't auto-generate
    if st.button("Generate New Plan 🔄", key="generate_plan_button"):
        with st.spinner("Creating your personalized weekly plan..."):
            try:
                user_fitness_goals = st.session_state.user.get('fitness_goals', [])
                if not user_fitness_goals:
                    user_fitness_goals = [DEFAULT_GOAL]

                user_data = {
                    'weight': st.session_state.user.get('weight', DEFAULT_WEIGHT),
                    'height': st.session_state.user.get('height', DEFAULT_HEIGHT),
                    'fitness_goals': user_fitness_goals,
                    'experience_level': selected_level,
                    'preferred_rest_day': selected_rest_day,
                    'workout_duration': workout_duration,
                    'start_date': start_date.isoformat(),
                    'date_range': formatted_db_dates
                }

                st.session_state.weekly_plan = generate_weekly_plan(user_data, collections)
                st.success("New plan generated successfully!")
                st.rerun()  # Rerun to display the plan
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")
                return


@auth_required
def main() -> None:
    """
    Main function to run the Workout Creator page.

    This page allows users to generate personalized weekly workout plans
    based on their preferences and fitness goals.
    """
    st.set_page_config(page_title="Workout Creator", page_icon="📋", layout="centered")
    inject_custom_styles()

    get_weekly_plan_tab()


# Run the application
main()
