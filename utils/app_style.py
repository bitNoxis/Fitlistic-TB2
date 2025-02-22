import streamlit as st


def inject_custom_styles():
    st.markdown("""
    <style>
    a[data-testid="stSidebarNavLink"] {
        font-size: 24px;
    }
    div[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][href$="/login"] {
        display: none !important;
    }
    div[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][href$="/Register"] {
        display: none !important;
    }
    div[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][href$="/Start"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)
