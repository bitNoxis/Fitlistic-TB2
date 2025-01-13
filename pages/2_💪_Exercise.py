import streamlit as st
from PIL import Image
import random
from utils.helpers import check_user_name, EXERCISE_PAIRS, QUOTATIONS

# Page config
st.set_page_config(page_title="Exercise", page_icon="💪", layout="centered")

# Check if user has entered name
user_name = check_user_name()

# Initialize session state for workout status
if 'workout_completed' not in st.session_state:
    st.session_state.workout_completed = False


def reset_workout():
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

    st.title(f"Congratulations {user_name}!")
    st.subheader("You have completed your session!")

    # Display random motivational quote
    quote = random.choice(list(QUOTATIONS.values()))
    st.markdown(f"*{quote}*")

    if st.button("Start New Workout", type="primary", on_click=reset_workout):
        st.rerun()