"""Model and threshold page: Metrics, drivers, ROC curve, model comparison, contact sliders."""

import streamlit as st
from app.ui import render_section_header


def render() -> None:
    render_section_header("Model and threshold", "Evaluation metrics, feature drivers, and economic threshold optimization.")
    st.info("Model and threshold placeholder.")
