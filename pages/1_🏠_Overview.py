import streamlit as st
from PIL import Image
from utils.auth_helper import auth_required
import plotly.graph_objects as go


@auth_required
def overview_page():
    # Page config
    st.set_page_config(page_title="Overview", page_icon="🏠", layout="centered")

    # Data points
    x = ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]
    y = [0, 10, 20, 30, 43]

    # Create the graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        line=dict(color='#4B89DC', width=3),  # Modern blue line
        marker=dict(
            size=12,
            color='#E74C3C',  # Red markers
            line=dict(width=2, color='white')  # White border around markers
        )
    ))

    # Clean, minimal layout
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            showline=False,
            zeroline=False
        )
    )

    # Display in Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Wellbeing Score Section
    st.header("Wellbeing Score")
    try:
        score_img = Image.open("images/Score.png")
        st.image(score_img, width=335)
    except:
        st.warning("Score image not found")

    # Session Options
    st.header("Quick Start")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Fullbody Workout", type="primary", key="fullbody"):
            st.switch_page("pages/2_💪_Exercise.py")
        if st.button("Power Recovery", type="primary", key="recovery"):
            st.switch_page("pages/2_💪_Exercise.py")

    with col2:
        if st.button("Upperbody Workout", type="primary", key="upperbody"):
            st.switch_page("pages/2_💪_Exercise.py")
        if st.button("Lower Body", type="primary", key="lowerbody"):
            st.switch_page("pages/2_💪_Exercise.py")

    # Weekly Progress
    st.header("Weekly Progress")
    progress_data = {
        'Workouts Completed': 3,
        'Total Minutes': 45,
        'Calories Burned': 450
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Workouts", progress_data['Workouts Completed'])
    with col2:
        st.metric("Minutes", progress_data['Total Minutes'])
    with col3:
        st.metric("Calories", progress_data['Calories Burned'])


# Run the page
overview_page()
