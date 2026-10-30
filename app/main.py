"""RetainAI: Retention Console for Retail Broking.

Main Streamlit application entry point.
Groups navigation into Monitor, Plan, and Evaluate.
"""

import streamlit as st

from app.ui import inject_global_styles, render_empty_state
from app.data import data_ready
from app.views import (
    overview,
    risk_queue,
    segments_playbook,
    experiment_planner,
    model_threshold,
)

# Page configuration
st.set_page_config(
    page_title="RetainAI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject design tokens and typography
inject_global_styles()


def render_sidebar_nav() -> str:
    """Render grouped navigation sidebar matching SPEC.md."""
    st.sidebar.markdown(
        """
        <div style="padding: 12px 0 20px 0;">
            <div style="font-size: 20px; font-weight: 700; color: #17212B; letter-spacing: -0.3px;">RetainAI</div>
            <div style="font-size: 12px; color: #5A6572; margin-top: 2px;">Retention console</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_options = [
        "Overview",
        "Risk queue",
        "Segments and playbook",
        "Experiment planner",
        "Model and threshold",
    ]

    # Map options to their group for visual organization
    group_labels = {
        "Overview": "Monitor",
        "Risk queue": "Monitor",
        "Segments and playbook": "Plan",
        "Experiment planner": "Plan",
        "Model and threshold": "Evaluate",
    }

    # Allow URL query param navigation (e.g. ?page=Risk+queue)
    query_page = st.query_params.get("page")
    default_index = 0
    if query_page and query_page in nav_options:
        default_index = nav_options.index(query_page)

    selected_page = st.sidebar.radio(
        label="Navigation",
        options=nav_options,
        index=default_index,
        label_visibility="collapsed",
    )

    st.sidebar.markdown(
        """
        <div style="margin-top: 36px; padding-top: 16px; border-top: 1px solid #E2E5E9; font-size: 11px; color: #5A6572;">
            <div>Retail broking retention</div>
            <div style="margin-top: 4px;">Prediction: Day 14</div>
            <div>Dormancy: Day 61-90</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return selected_page


def main() -> None:
    """Main routing and execution logic."""
    selected_page = render_sidebar_nav()

    # Graceful missing data handling
    if not data_ready():
        render_empty_state(
            title="Data pipeline has not been executed",
            message="The SQLite database, user risk scores, and model artifacts were not found. Run the end-to-end data and training pipeline to generate the dataset.",
            command="python -m src.pipeline",
        )
        return

    # Route to selected page
    if selected_page == "Overview":
        overview.render()
    elif selected_page == "Risk queue":
        risk_queue.render()
    elif selected_page == "Segments and playbook":
        segments_playbook.render()
    elif selected_page == "Experiment planner":
        experiment_planner.render()
    elif selected_page == "Model and threshold":
        model_threshold.render()


if __name__ == "__main__":
    main()
