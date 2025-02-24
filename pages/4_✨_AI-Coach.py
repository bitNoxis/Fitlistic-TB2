import streamlit as st
from openai import OpenAI

from utils.app_style import inject_custom_styles
from utils.auth_helper import auth_required


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


def get_initial_message():
    user = st.session_state.user
    goals_str = ", ".join(user.get("fitness_goals", ["General Fitness"]))
    return f"""Hello {user['first_name']}! I'm your AI workout coach. I can help you with one time personalized 
    workouts, nutrition tips, and wellness advice. If you are looking for a full workout plan check out the Workout 
    Creator in the Sidebar. 
- Your current fitness goals are: {goals_str}

How would you like to work towards your goals today?"""


def calculate_bmi(weight, height):
    height_m = height / 100  # convert cm to m
    return weight / (height_m * height_m)


@auth_required
def main():
    st.set_page_config(page_title="AI Wellbeing Coach", page_icon="✨", layout="centered")
    inject_custom_styles()

    st.title(f"AI Coach️")
    initialize_chat_history()
    with st.sidebar:
        st.header(f"Ideas for one time workouts (based on your goals)")
        handle_sidebar_buttons()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    if prompt := st.chat_input("What kind of workout are you looking for?"):
        handle_chat_interaction(prompt)


def handle_sidebar_buttons():
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
    if not goals:
        if st.button("🏃‍♂️ Cardio Workout"):
            handle_workout_click("Create a 30-minute cardio workout for beginners")
        if st.button("💪 Full Body Workout"):
            handle_workout_click("Create a full-body workout for general fitness")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [{"role": "assistant", "content": get_initial_message()}]
        st.rerun()


def handle_workout_click(prompt):
    if 'messages' not in st.session_state:
        initialize_chat_history()
    st.session_state.messages.append({"role": "user", "content": prompt})
    full_response = get_ai_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()


def handle_chat_interaction(prompt):
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
            *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
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
    return f"""You are a knowledgeable holistic fitness coach who cares about both mental and physical health, as well as nutrition. Using the following user profile, provide balanced and personalized guidance:

- Fitness goals: {', '.join(goals)}
- Weight: {user.get('weight', 70)} kg
- Height: {user.get('height', 170)} cm
- BMI: {bmi:.1f}

Your recommendations should:
1. Include a mix of physical exercises and wellness practices.
2. Emphasize mental well-being, stress reduction, and mindfulness.
3. Offer nutritional tips and healthy eating advice.
4. Ensure safety, proper form, and sustainability.
5. Adapt to the user's current fitness level and lifestyle.

Always prioritize overall well-being and a balanced approach in your guidance.
"""


main()
