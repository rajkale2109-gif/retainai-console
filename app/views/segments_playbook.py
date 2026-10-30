"""Segments and playbook page: Expected value by segment, summary table, playbook per segment."""

import streamlit as st
from app.ui import render_section_header


def render() -> None:
    render_section_header("Segments and playbook", "Behavioural segment economics, save rates, and playbook interventions.")
    st.info("Segments and playbook placeholder.")
