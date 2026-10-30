"""Feature extraction and preprocessing pipeline for RetainAI."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sqlite3
import pandas as pd
import numpy as np

from src.config import DB_PATH, SQL_DIR


# Plain-language feature names for PMs and business stakeholders
FEATURE_NAMES_MAP: Dict[str, str] = {
    "is_funded_d14": "Account funded status",
    "total_funded_amount_d14": "Total deposit amount (₹)",
    "funding_count_d14": "Number of deposits",
    "days_to_first_funding": "Days to first deposit",
    "session_count_d14": "App sessions count",
    "active_days_d14": "Active days count",
    "total_screens_viewed_d14": "Screens viewed",
    "avg_screens_per_session_d14": "Average screens per session",
    "total_watchlist_adds_d14": "Watchlist stock additions",
    "max_watchlist_adds_session_d14": "Max watchlist adds in one session",
    "last_session_day_d14": "Latest active session day",
    "trade_count_d14": "Number of trades",
    "total_trade_value_d14": "Total turnover value (₹)",
    "total_realized_pnl_d14": "Total realized P&L (₹)",
    "worst_trade_pnl_d14": "Worst single trade P&L (₹)",
    "loss_trades_count_d14": "Unprofitable trades count",
    "win_trades_count_d14": "Profitable trades count",
    "days_to_first_trade_d14": "Days to first trade",
    "fno_trades_count_d14": "F&O derivative trades",
    "delivery_trades_count_d14": "Equity delivery trades",
    "ticket_count_d14": "Support tickets count",
    "kyc_ticket_count_d14": "KYC support tickets",
    "funding_ticket_count_d14": "Funding support tickets",
    "kyc_completed_d14": "KYC completed within 14 days",
    "days_to_kyc": "Days to KYC completion",
    "acquisition_channel": "Acquisition channel",
    "city_tier": "City tier",
    "age_band": "Age band",
}


def extract_features(conn: sqlite3.Connection) -> pd.DataFrame:
    """Execute sql/features_day14.sql to extract day-14 behavioural features.

    Strictly queries events occurring on or before signup_date + 14 days.
    """
    sql_path = SQL_DIR / "features_day14.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        query = f.read()
    return pd.read_sql_query(query, conn)


def extract_labels(conn: sqlite3.Connection) -> pd.DataFrame:
    """Execute sql/label_dormancy.sql to extract ground truth dormancy labels."""
    sql_path = SQL_DIR / "label_dormancy.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        query = f.read()
    return pd.read_sql_query(query, conn)


def load_raw_dataset(conn: Optional[sqlite3.Connection] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load extracted features and ground truth labels from the SQLite database."""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True

    try:
        features_df = extract_features(conn)
        labels_df = extract_labels(conn)
    finally:
        if should_close:
            conn.close()

    return features_df, labels_df


def prepare_feature_matrix(
    features_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str]]:
    """Clean and encode features for machine learning models.

    - Fills missing demographic values with 'Unknown'.
    - Fills null durations (days_to_trade, days_to_funding, days_to_kyc) with -1.
    - One-hot encodes categorical columns.
    """
    df = features_df.copy()

    # Handle missing demographics
    df["city_tier"] = df["city_tier"].fillna("Missing")
    df["age_band"] = df["age_band"].fillna("Missing")

    # Handle timing features where null indicates event did not occur within day 14
    for col in ["days_to_kyc", "days_to_first_funding", "days_to_first_trade_d14", "last_session_day_d14"]:
        if col in df.columns:
            df[col] = df[col].fillna(-1.0)

    # Categorical columns to encode
    cat_cols = ["acquisition_channel", "city_tier", "age_band"]
    encoded_df = pd.get_dummies(df, columns=cat_cols, drop_first=False, dtype=float)

    # Exclude metadata and target columns from model features
    meta_cols = ["user_id", "signup_date", "is_dormant"]
    feature_cols = [c for c in encoded_df.columns if c not in meta_cols]

    return encoded_df, feature_cols
