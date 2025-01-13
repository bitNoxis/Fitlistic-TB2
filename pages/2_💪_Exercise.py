import streamlit as st
from PIL import Image
import random
from utils.auth_helper import auth_required

# Exercise pairs
EXERCISE_PAIRS = [
    ("images/Squat.png", "15x3 Squat"),
    ("images/Dips.png", "10x4 Dips"),
    ("images/Meditate.png", "3 Minute Breathwork"),
    ("images/Plank.png", "30 Seconds Plank"),
    ("images/Stretch.png", "1 Minute Stretch")
]

# Motivational quotes
QUOTATIONS = {
    1: "Exercises is king and nutrition is queen. Combine the two and you will have a kingdom.",
    2: "The only bad workout is the one that didn't happen.",
    3: "Fitness is not about being better than you used to be."
}


@auth_required
def exercise_page():
    # Page config
    st.set_page_config(page_title="Exercise", page_icon="💪", layout="centered")

    # Initialize workout state if needed
    if 'workout_completed' not in st.session_state:
        st.session_state.workout_completed = False

    # Main content
    if not st.session_state.workout_completed:
        st.title("Exercise Session")
        st.subheader("5 Exercises | 15 Minutes | 150 Calorie Burn")

        # Display exercises
        for img_path, description in EXERCISE_PAIRS:
            col1, col2 = st.columns([1, 4])
            try:
                with col1:
                    img = Image.open(img_path)
                    img = img.resize((50, 50))
                    st.image(img)
                with col2:
                    st.write(description)
            except:
                st.warning(f"Could not load image: {img_path}")

        if st.button("Complete Workout", type="primary"):
            st.session_state.workout_completed = True
            st.rerun()

    else:
        # Completion screen
        try:
            finish_img = Image.open("images/Finish.png")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(finish_img, width=255)
        except:
            st.warning("Finish image not found")

        st.title(f"Congratulations {st.session_state.user['first_name']}!")
        st.subheader("You have completed your session!")

        # Display random motivational quote
        quote = random.choice(list(QUOTATIONS.values()))
        st.markdown(f"*{quote}*")

        if st.button("Start New Workout", type="primary"):
            st.session_state.workout_completed = False
            st.rerun()


# Run the page
exercise_page()
