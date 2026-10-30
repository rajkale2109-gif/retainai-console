"""Overview page: Five-figure metric strip, funnel, cohort retention heatmap, time to first trade."""

import streamlit as st
from app.ui import render_section_header


def render() -> None:
    render_section_header("Overview", "High-level conversion funnel, retention heatmap, and early trading patterns.")
    st.info("Overview page content placeholder.")
