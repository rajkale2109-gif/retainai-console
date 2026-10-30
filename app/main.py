"""RetainAI: Retention Console for Retail Broking.

Main Streamlit application entry point.
Institutional Terminal Shell featuring:
- Global telemetry Top Bar & Theme Switcher (Dark/Light)
- Compact Grouped Left Rail Navigation (Monitor, Plan, Evaluate)
- Fixed Bottom Status Bar
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path when running `streamlit run app/main.py`
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from app.ui import (
    inject_terminal_styles,
    render_top_bar,
    render_sidebar_rail,
    render_status_bar,
    render_empty_state,
)
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
    page_title="RetainAI | Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject terminal design system and typography
inject_terminal_styles()


def main() -> None:
    """Main terminal routing and execution logic."""
    selected_page = render_sidebar_rail()

    # Render global top telemetry bar
    render_top_bar(current_page=selected_page)

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
        render_status_bar(rows_shown=20000, active_filters="Cohort Base (2025)", approved_count=0)
    elif selected_page == "Risk queue":
        risk_queue.render()
        # Status line is rendered inside risk_queue with active filter counts
    elif selected_page == "Segments and playbook":
        segments_playbook.render()
        render_status_bar(rows_shown=20000, active_filters="5 Segment Classes", approved_count=0)
    elif selected_page == "Experiment planner":
        experiment_planner.render()
        render_status_bar(rows_shown=2840, active_filters="Power 80% | Alpha 0.05", approved_count=0)
    elif selected_page == "Model and threshold":
        model_threshold.render()
        render_status_bar(rows_shown=4000, active_filters="Hold-out (Signups >= 2025-10-01)", approved_count=0)


if __name__ == "__main__":
    main()
