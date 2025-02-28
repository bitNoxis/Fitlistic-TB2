"""
AI Wellbeing Coach Module

This module provides an AI-powered coaching interface for fitness and wellness guidance,
allowing users to get personalized one time workout recommendations and health advice based on
their fitness goals and profile information.
"""

from typing import List

import streamlit as st
from openai import OpenAI

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required

# Constants
OPENAI_MODEL = "gpt-3.5-turbo-0125"
DEFAULT_WEIGHT = 70  # kg
DEFAULT_HEIGHT = 170  # cm
DEFAULT_GOAL = "General Fitness"


def load_api_key() -> str:
    """
    Load OpenAI API key from Streamlit secrets.

    Returns:
        API key string

    Raises:
        Exception if API key is not found
    """
    try:
        api_key = st.secrets['openai-key']
        if not api_key:
            raise ValueError("Empty API key")
        return api_key
    except (KeyError, ValueError):
        st.error('OpenAI API key not found in secrets.')
        st.stop()


@st.cache_resource
def get_openai_client() -> OpenAI:
    """
    Initialize and cache OpenAI client with API key.

    Returns:
        OpenAI client instance
    """
    return OpenAI(api_key=load_api_key())


def initialize_chat_history() -> None:
    """
    Initialize chat history with personalized welcome message if not already present.
    """
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": get_initial_message()}
        ]


def get_initial_message() -> str:
    """
    Generate personalized welcome message based on user profile.

    Returns:
        Welcome message string
    """
    user = st.session_state.user
    goals_str = ", ".join(user.get("fitness_goals", [DEFAULT_GOAL]))
    return f"""Hello {user['first_name']}! I'm your AI workout coach. I can help you with one time personalized 
    workouts, nutrition tips, and wellness advice. If you are looking for a full workout plan check out the Workout 
    Creator in the Sidebar. 
- Your current fitness goals are: {goals_str}

How would you like to work towards your goals today?"""


def calculate_bmi(weight: float, height: float) -> float:
    """
    Calculate Body Mass Index (BMI) from weight and height.

    Args:
        weight: Weight in kg
        height: Height in cm

    Returns:
        BMI value as float
    """
    height_m = height / 100  # convert cm to m
    return weight / (height_m * height_m)


def get_system_prompt() -> str:
    """
    Generate system prompt for OpenAI based on user profile.

    Returns:
        System prompt string
    """
    user = st.session_state.user
    bmi = calculate_bmi(
        user.get("weight", DEFAULT_WEIGHT),
        user.get("height", DEFAULT_HEIGHT)
    )
    goals = user.get("fitness_goals", [DEFAULT_GOAL])

    return f"""You are a knowledgeable holistic fitness coach who cares about both mental and physical health, as well as nutrition. Using the following user profile, provide balanced and personalized guidance:

If you are asked about a long term workout plan that has more than one workout for one day, dont answer. Just say that the user can create one in the Workout creator
If it makes sense smartly advertise the Workout Creator from the App 

- Fitness goals: {', '.join(goals)}
- Weight: {user.get('weight', DEFAULT_WEIGHT)} kg
- Height: {user.get('height', DEFAULT_HEIGHT)} cm
- BMI: {bmi:.1f}

Your recommendations should:
1. Include a mix of physical exercises and wellness practices.
2. Emphasize mental well-being, stress reduction, and mindfulness.
3. Offer nutritional tips and healthy eating advice.
4. Ensure safety, proper form, and sustainability.
5. Adapt to the user's current fitness level and lifestyle.

Always prioritize overall well-being and a balanced approach in your guidance.
"""


def get_ai_response(prompt: str) -> str:
    """
    Get AI-generated response to user prompt.

    Args:
        prompt: User input text

    Returns:
        AI-generated response
    """
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            ],
            stream=True
        )

        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
        return full_response
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again."


def display_chat_history() -> None:
    """
    Display the current chat history in the UI.
    """
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def handle_chat_input() -> None:
    """
    Handle new user chat input.
    """
    if prompt := st.chat_input("What kind of workout are you looking for?"):
        handle_chat_interaction(prompt)


def handle_chat_interaction(prompt: str) -> None:
    """
    Process user input, display in chat, and get AI response.

    Args:
        prompt: User input text
    """
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # Get and display AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = get_ai_response(prompt)
        message_placeholder.markdown(full_response)

    # Add AI response to history
    st.session_state.messages.append({"role": "assistant", "content": full_response})


def handle_workout_click(prompt: str) -> None:
    """
    Handle sidebar workout button click.

    Args:
        prompt: Workout prompt to send to AI
    """
    if 'messages' not in st.session_state:
        initialize_chat_history()

    st.session_state.messages.append({"role": "user", "content": prompt})
    full_response = get_ai_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()


def display_goal_based_buttons(goals: List[str]) -> None:
    """
    Display sidebar buttons based on user's fitness goals.

    Args:
        goals: List of user's fitness goals
    """
    if "Weight Loss" in goals:
        if st.button("🏃‍♂️ Fat Burning Workout"):
            handle_workout_click("Create a one time fat burning HIIT workout suitable for my fitness level")

    if "Muscle Gain" in goals:
        if st.button("💪 Strength Training"):
            handle_workout_click("Create a one time strength training workout focused on muscle gain")

    if "Flexibility" in goals:
        if st.button("🧘‍♀️ Flexibility Routine"):
            handle_workout_click("Create a one time flexibility and mobility routine")

    if "Better Mental Health" in goals:
        if st.button("🧠 Mental Health Boost"):
            handle_workout_click(
                "Create a one time workout that incorporates mindfulness and gentle exercises for better mental health")

    if "Stress Resilience" in goals:
        if st.button("😌 Stress Resilience"):
            handle_workout_click(
                "Create a one time workout that combines light cardio with stress management techniques")

    if "General Fitness" in goals or not goals:
        if st.button("🏋️‍♂️ Full Body Workout"):
            handle_workout_click("Create a one time full body workout for general fitness")


def display_fallback_buttons() -> None:
    """
    Display fallback buttons when no specific goals are selected.
    """
    if st.button("🏃‍♂️ Cardio Workout"):
        handle_workout_click("Create a one time 30-minute cardio workout for beginners")


def display_clear_chat_button() -> None:
    """
    Display button to clear chat history.
    """
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [{"role": "assistant", "content": get_initial_message()}]
        st.rerun()


def handle_sidebar_buttons() -> None:
    """
    Handle all sidebar button logic.
    """
    goals = st.session_state.user.get('fitness_goals', [])

    # Display goal-based buttons
    display_goal_based_buttons(goals)

    # Fallback options if no specific goals are selected
    if not goals:
        display_fallback_buttons()

    # Always show clear chat option
    display_clear_chat_button()


@auth_required
def main() -> None:
    """
    Main function to run the AI Wellbeing Coach interface.

    This page provides an interactive chat interface for users to get
    personalized workout and wellness recommendations.
    """
    # Configure the page
    st.set_page_config(page_title="AI Wellbeing Coach", page_icon="✨", layout="centered")
    inject_custom_styles()

    # Display page title
    st.title("✨ AI Wellbeing Coach️")

    # Initialize chat if needed
    initialize_chat_history()

    # Setup sidebar
    with st.sidebar:
        st.header("Ideas for one time workouts (based on your goals)")
        handle_sidebar_buttons()

    # Display chat history
    display_chat_history()

    # Handle new user input
    handle_chat_input()


# Run the main function
main()
