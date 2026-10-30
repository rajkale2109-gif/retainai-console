"""Risk queue page: Filters, ranked table, CSV export, per-user drivers and recommended message."""

import streamlit as st
from app.ui import render_section_header


def render() -> None:
    render_section_header("Risk queue", "Prioritized intervention queue sorted by expected return.")
    st.info("Risk queue placeholder.")
