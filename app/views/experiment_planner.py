"""Experiment planner page: Sample-size calculator, decision rule, result read-out."""

import streamlit as st
from app.ui import render_section_header


def render() -> None:
    render_section_header("Experiment planner", "A/B pilot sizing and statistical significance testing.")
    st.info("Experiment planner placeholder.")
