"""
UI Style Helper Module

This module provides functions for applying custom styles to 
different parts of the application.
"""

import streamlit as st


def inject_custom_styles():
    """
    Injects custom CSS styles into the Streamlit application.

    This function applies the following style changes:
    - Increases sidebar navigation link font size
    - Hides specific navigation links (login, register, and start pages)
      from appearing in the sidebar
    """
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


def apply_auth_page_styling():
    """
    Apply custom CSS to hide navigation elements on authentication pages.

    This function hides all navigation and UI elements to create a clean
    login/registration experience without distractions.
    """
    st.markdown(
        """
        <style>
            /* Hide sidebar navigation */
            div[data-testid="stSidebarNav"] {display: none !important;}

            /* Hide menu button */
            button[kind="header"] {display: none !important;}

            /* Hide hamburger menu */
            .stApp > header {display: none !important;}

            /* Hide Streamlit footer */
            footer {display: none !important;}

            /* Hide all navigation elements */
            .stDeployButton {display: none !important;}
            section[data-testid="stSidebar"] {display: none !important;}

            /* Hide full-screen button */
            [data-testid="stElementToolbar"] {display: none !important;}

            /* Critical: Hide sidebar collapse control */
            [data-testid="collapsedControl"] {display: none !important;}

            /* Additional button hiding */
            button[kind="menuButton"] {display: none !important;}
            button[data-testid="baseButton-header"] {display: none !important;}
        </style>
        """,
        unsafe_allow_html=True
    )
