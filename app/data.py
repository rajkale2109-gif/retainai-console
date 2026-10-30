"""Data loading and caching layer for the Streamlit application."""

import json
import sqlite3
from typing import Any, Dict, Optional
import pandas as pd
import streamlit as st

from src.config import (
    DB_PATH,
    METRICS_PATH,
    SCORES_PATH,
    SQL_DIR,
)


def data_ready() -> bool:
    """Check whether the pipeline data and artifacts exist."""
    return DB_PATH.exists() and SCORES_PATH.exists() and METRICS_PATH.exists()


@st.cache_data(show_spinner=False)
def get_scores() -> pd.DataFrame:
    """Load user scores, predictions, and segment allocations."""
    if not SCORES_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(SCORES_PATH)


@st.cache_data(show_spinner=False)
def get_metrics() -> Dict[str, Any]:
    """Load model hold-out evaluation metrics and feature importances."""
    if not METRICS_PATH.exists():
        return {}
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def get_funnel() -> pd.DataFrame:
    """Execute sql/funnel.sql via SQLite."""
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_DIR / "funnel.sql", "r", encoding="utf-8") as f:
            query = f.read()
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def get_retention_cohorts() -> pd.DataFrame:
    """Execute sql/retention.sql via SQLite."""
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_DIR / "retention.sql", "r", encoding="utf-8") as f:
            query = f.read()
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def get_time_to_first_trade() -> pd.DataFrame:
    """Execute sql/time_to_first_trade.sql via SQLite."""
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_DIR / "time_to_first_trade.sql", "r", encoding="utf-8") as f:
            query = f.read()
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()
