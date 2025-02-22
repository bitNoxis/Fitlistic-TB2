# pages/4_✨_AI-Coach.py
import streamlit as st
from openai import OpenAI
from datetime import datetime

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required
from utils.mongo_helper import get_collection
from utils.holistic_planner import HolisticPlanGenerator


def load_api_key():
    """Load API key from Streamlit secrets"""
    api_key = st.secrets['openai-key']
    if not api_key:
        st.error('OpenAI API key not found in secrets.')
        st.stop()
    return api_key


@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client with API key"""
    return OpenAI(api_key=load_api_key())


def initialize_chat_history():
    """Initialize chat history with personalized message"""
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": get_initial_message()}
        ]


def get_weekly_plan_tab():
    """Display the weekly plan tab content"""
    st.header("Your Weekly Holistic Plan 🎯")

    collections = {
        "exercises": get_collection("fitlistic", "exercises"),
        "breathwork": get_collection("fitlistic", "breathwork_techniques"),
        "meditation": get_collection("fitlistic", "meditation_templates"),
        "stretching": get_collection("fitlistic", "stretching_routines"),
        "cool_downs": get_collection("fitlistic", "cool_downs"),
        "warm_ups": get_collection("fitlistic", "warm_ups")
    }

    # Überprüfe, ob alle Collections erfolgreich initialisiert wurden
    if any(coll is None for coll in collections.values()):
        st.error("Failed to connect to one or more required collections")
        return

    # Create planner instance
    planner = HolisticPlanGenerator(collections)

    # Generate/Display Plan
    if 'weekly_plan' not in st.session_state or st.button("Generate New Plan 🔄"):
        with st.spinner("Creating your personalized weekly plan..."):
            try:
                user_data = {
                    'weight': st.session_state.user.get('weight', 70),
                    'height': st.session_state.user.get('height', 170),
                    'fitness_goals': st.session_state.user.get('fitness_goals', ['General Fitness']),
                    'experience_level': st.session_state.user.get('experience_level', 'beginner')
                }

                st.session_state.weekly_plan = planner.generateWeeklyPlan(user_data)
                st.success("New plan generated successfully!")
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")
                return

    if 'weekly_plan' in st.session_state:
        plan = st.session_state.weekly_plan

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

        # Create tabs for each day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday']
        tabs = st.tabs(days)

        for day, tab in zip(days, tabs):
            with tab:
                day_lower = day.lower()
                if day_lower in plan['schedule']:
                    display_day_schedule(plan['schedule'][day_lower], day)


def get_initial_message():
    user = st.session_state.user
    goals_str = ", ".join(user.get("fitness_goals", ["General Fitness"]))
    bmi = calculate_bmi(user.get("weight", 70), user.get("height", 170))

    return f"""Hello {user['first_name']}! I'm your AI workout coach and I see that:
- Your fitness goals are: {goals_str}
- Current weight: {user.get('weight', 70)} kg
- Height: {user.get('height', 170)} cm
- BMI: {bmi:.1f}

How would you like to work towards your goals today?"""


def calculate_bmi(weight, height):
    height_m = height / 100  # convert cm to m
    return weight / (height_m * height_m)


def display_day_schedule(schedule, day_name):
    st.subheader(f"{day_name} - {schedule['type']}")

    for block in schedule['schedule']:
        with st.expander(f"{format_time(block['time'])} - {block['activity']['name']} ({block['duration']} min)"):
            if 'exercises' in block['activity']:
                for ex in block['activity']['exercises']:
                    st.markdown(f"**{ex['name']}**")
                    st.markdown("Form cues:")
                    for cue in ex['form_cues']:
                        st.markdown(f"- {cue}")
                    st.markdown(f"Sets: {ex['sets']} | Reps: {ex['reps']}")
            elif 'instructions' in block['activity']:
                st.markdown("Instructions:")
                for instruction in block['activity']['instructions']:
                    st.markdown(f"- {instruction}")


def format_time(time_str):
    return datetime.strptime(time_str, '%H:%M').strftime('%I:%M %p')


@auth_required
def main():
    st.set_page_config(
        page_title="AI Wellbeing Coach",
        page_icon="✨",
        layout="wide"
    )
    inject_custom_styles()

    # Create tabs for chat and weekly plan
    tab1, tab2 = st.tabs(["💬 AI Coach Chat", "📅 Weekly Plan"])

    with tab1:
        # Original chat functionality
        st.title(f"Hey, {st.session_state.user['first_name']}! 🏋️‍♂️")
        initialize_chat_history()

        with st.sidebar:
            st.header(f"{st.session_state.user['first_name']}'s Quick Options")
            handle_sidebar_buttons()

        # Display chat history and input
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        if prompt := st.chat_input("What kind of workout are you looking for?"):
            handle_chat_interaction(prompt)

    with tab2:
        get_weekly_plan_tab()


def handle_sidebar_buttons():
    """Handle sidebar button clicks"""
    goals = st.session_state.user.get('fitness_goals', [])

    if "Weight Loss" in goals:
        if st.button("🏃‍♂️ Fat Burning Workout"):
            handle_workout_click("Create a fat burning HIIT workout suitable for my fitness level")

    if "Muscle Gain" in goals:
        if st.button("💪 Strength Training"):
            handle_workout_click("Create a strength training workout focused on muscle gain")

    if "Flexibility" in goals:
        if st.button("🧘‍♀️ Flexibility"):
            handle_workout_click("Create a flexibility and mobility routine")

    if "Endurance" in goals:
        if st.button("🏃 Endurance Training"):
            handle_workout_click("Create an endurance-focused workout")

    if not goals:  # If no specific goals are set, show general options
        if st.button("🏃‍♂️ Cardio Workout"):
            handle_workout_click("Create a 30-minute cardio workout for beginners")
        if st.button("💪 Full Body Workout"):
            handle_workout_click("Create a full-body workout for general fitness")

    # Clear chat history
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": get_initial_message()}
        ]
        st.rerun()


def handle_workout_click(prompt):
    if 'messages' not in st.session_state:
        initialize_chat_history()

    st.session_state.messages.append({"role": "user", "content": prompt})
    full_response = get_ai_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()


def handle_chat_interaction(prompt):
    """Handle chat input interactions"""
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = get_ai_response(prompt)
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})


def get_ai_response(prompt):
    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": get_system_prompt()},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        ],
        stream=True
    )

    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content

    return full_response


def get_system_prompt():
    user = st.session_state.user
    bmi = calculate_bmi(user.get("weight", 70), user.get("height", 170))
    goals = user.get("fitness_goals", ["General Fitness"])

    return f"""You are a knowledgeable fitness coach. Create personalized workouts based on the following user profile:
- Fitness goals: {', '.join(goals)}
- Current weight: {user.get('weight', 70)} kg
- Height: {user.get('height', 170)} cm
- BMI: {bmi:.1f}

Create workouts that:
1. Align with the user's fitness goals
2. Are appropriate for their current fitness level
3. Include warm-up and cool-down routines
4. Provide clear instructions for proper form
5. Include modifications if needed
6. Consider their BMI for appropriate exercise selection

Always prioritize safety and proper form in your recommendations."""


if __name__ == "__main__":
    main()
