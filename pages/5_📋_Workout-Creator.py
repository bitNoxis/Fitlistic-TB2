from datetime import datetime

import streamlit as st

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.holistic_planner import generate_weekly_plan
from utils.mongo_helper import get_collection, save_workout_plan


def get_weekly_plan_tab():
    st.title("📋 Workout Creator")
    st.header("Generate your 7-Day Holistic Fitness Plan")

    col1, col2 = st.columns(2)

    with col1:
        # Experience Level Selector with multiselect
        experience_level = st.multiselect(
            "Select your experience level",
            options=["beginner", "intermediate", "advanced"],
            default=["beginner"],
            key="experience_selector",
            help="This will adjust the intensity and complexity of your workouts"
        )
        # Use the first selected experience level
        selected_level = experience_level[0] if experience_level else "beginner"

    with col2:
        # Rest day selector with multiselect
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        preferred_rest_day = st.multiselect(
            "Choose your preferred rest day",
            options=days,
            default=["Sunday"],
            key="rest_day_selector",
            help="Select the day that best fits your schedule for rest and recovery"
        )
        # Use the first selected rest day
        selected_rest_day = preferred_rest_day[0] if preferred_rest_day else "Sunday"

    # Workout duration selection
    workout_duration = st.selectbox(
        "Main workout duration (minutes)",
        options=[30, 45, 60, 90],
        key="workout_duration",
        help="Total time for your main exercises"
    )

    # Initialize required collections
    collections = {
        "exercises": get_collection("fitlistic", "exercises"),
        "breathwork": get_collection("fitlistic", "breathwork_techniques"),
        "meditation": get_collection("fitlistic", "meditation_templates"),
        "stretching": get_collection("fitlistic", "stretching_routines"),
        "cool_downs": get_collection("fitlistic", "cool_downs"),
        "warm_ups": get_collection("fitlistic", "warm_ups")
    }

    # Check if all collections are available
    if any(coll is None for coll in collections.values()):
        st.error("Failed to connect to one or more required collections")
        return

    # Generate the weekly plan
    if 'weekly_plan' not in st.session_state or st.button("Generate New Plan 🔄"):
        with st.spinner("Creating your personalized weekly plan..."):
            try:
                user_fitness_goals = st.session_state.user.get('fitness_goals', [])
                if not user_fitness_goals:
                    user_fitness_goals = ['General Fitness']

                user_data = {
                    'weight': st.session_state.user.get('weight', 70),
                    'height': st.session_state.user.get('height', 170),
                    'fitness_goals': user_fitness_goals,
                    'experience_level': selected_level,
                    'preferred_rest_day': selected_rest_day.lower(),
                    'workout_duration': workout_duration
                }

                st.session_state.weekly_plan = generate_weekly_plan(user_data, collections)
                st.success("New plan generated successfully!")
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")
                return

    if 'weekly_plan' in st.session_state:
        display_weekly_plan(st.session_state.weekly_plan)

        def reset_exercise_view():
            if "viewed_day" in st.session_state:
                del st.session_state.viewed_day

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Save & Activate Plan"):
                user_id = str(st.session_state.user.get('_id'))
                success, message = save_workout_plan(user_id, st.session_state.weekly_plan)

                if success:
                    st.success("Workout plan saved successfully!")
                    if st.button("Start Workout"):
                        st.switch_page("pages/2_💪_Exercise.py?new_plan=true")
                else:
                    st.error(f"Failed to save plan: {message}")


def display_weekly_plan(plan):
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        total_workouts = sum(1 for day in plan['schedule'].values()
                             if day['type'] != 'Rest & Rejuvenation')
        st.metric("Weekly Workouts", total_workouts)
    with col2:
        total_minutes = sum(
            sum(block['duration'] for block in day['schedule'])
            for day in plan['schedule'].values()
        )
        st.metric("Total Minutes", total_minutes)
    with col3:
        active_days = len([day for day in plan['schedule'].values()
                           if day['type'] != 'Rest & Rejuvenation'])
        st.metric("Active Days", active_days)

    # Create tabs for each day of the week
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    tabs = st.tabs(days)

    for day, tab in zip(days, tabs):
        with tab:
            day_lower = day.lower()
            if day_lower in plan['schedule']:
                day_schedule = plan['schedule'][day_lower]
                if day_schedule['type'] == 'Rest & Rejuvenation':
                    display_rest_day_message()
                else:
                    display_day_schedule(day_schedule, day)


def display_rest_day_message():
    st.markdown("""
    ### 🌟 Rest Day! Time to Recharge! 

    Today is your well-deserved rest day! Remember:
    - 😴 Rest is when your body gets stronger
    - 🧘‍♀️ Light stretching and walks are a perfect way to optimize recovery
    - 🎮 Enjoy some guilt-free relaxation
    - 🥗 Focus on good nutrition and hydration
    """)


def display_day_schedule(schedule, day_name):
    st.subheader(f"{day_name} - {schedule.get('type', 'No type')}")

    for block in schedule.get('schedule', []):
        activity = block.get("activity", {})
        if not activity:
            st.markdown("No activity information available for this block.")
            continue

        activity_name = activity.get("name", "Unnamed Activity")
        duration = block.get("duration", "N/A")

        expander_title = f"{activity_name} ({duration} min)"
        with st.expander(expander_title):
            # Handle stretching routines with sequences
            sequence = activity.get("sequence", [])
            if sequence and isinstance(sequence, list):
                for exercise in sequence:
                    if isinstance(exercise, dict):
                        st.markdown(f"**{exercise.get('name', 'Unnamed Exercise')}**")
                        if 'duration' in exercise:
                            st.markdown(f"Duration: {exercise['duration']}")
                        if 'reps' in exercise:
                            st.markdown(f"Reps: {exercise['reps']}")

                        instructions = exercise.get('instructions', [])
                        if instructions:
                            st.markdown("Instructions:")
                            for instruction in instructions:
                                st.markdown(f"- {instruction}")

                        target_muscles = exercise.get('target_muscles', [])
                        if target_muscles:
                            st.markdown(f"Target muscles: {', '.join(target_muscles)}")
                        st.markdown("---")

            # Handle breathwork with steps
            steps = activity.get("steps", [])
            if steps and isinstance(steps, (list, str)):
                st.markdown("**Steps:**")
                if isinstance(steps, list):
                    for step in steps:
                        st.markdown(f"- {step}")
                else:
                    for step in steps.split('\n'):
                        st.markdown(f"- {step}")

            # Handle meditation with steps
            meditation_steps = activity.get("steps", [])
            if meditation_steps and isinstance(meditation_steps, list):
                for step in meditation_steps:
                    if isinstance(step, dict):
                        st.markdown(f"**Phase: {step.get('phase', 'Unknown phase')}**")
                        duration = step.get('duration_minutes')
                        if duration:
                            st.markdown(f"Duration: {duration} minutes")

                        instructions = step.get('instructions', [])
                        if instructions:
                            st.markdown("Instructions:")
                            for instruction in instructions:
                                st.markdown(f"- {instruction}")
                        st.markdown("---")

            # Handle regular exercises
            exercises = activity.get("exercises", [])
            if exercises and isinstance(exercises, list):
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

            # Show target areas if available
            target_areas = activity.get("target_areas", [])
            if target_areas and isinstance(target_areas, list):
                st.markdown(f"\n**Target Areas:** {', '.join(target_areas)}")


def format_time(time_str):
    return datetime.strptime(time_str, '%H:%M').strftime('%I:%M %p')


@auth_required
def main():
    st.set_page_config(page_title="AI Wellbeing Coach", page_icon="✨", layout="centered")
    inject_custom_styles()

    get_weekly_plan_tab()


main()
