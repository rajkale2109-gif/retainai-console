"""Leakage test for Day-14 feature extraction.

SPEC.md Requirement:
"pytest must pass, including a test proving features ignore anything after day 14."
"Write the day-14 leakage test first: delete all activity after day 14 and assert the features do not change."
"""

import sqlite3
import shutil
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from src.config import DB_PATH
from src.features import extract_features


@pytest.fixture
def test_db_copy(tmp_path: Path) -> Path:
    """Create a temporary isolated copy of the database for destructive testing."""
    assert DB_PATH.exists(), f"Database does not exist at {DB_PATH}. Run src.build_db first."
    temp_db = tmp_path / "test_retainai.db"
    shutil.copy2(DB_PATH, temp_db)
    return temp_db


def test_day14_feature_leakage_pruning(test_db_copy: Path):
    """Assert that deleting all activity after day 14 leaves extracted features identical."""
    conn = sqlite3.connect(test_db_copy)

    # 1. Extract baseline features from the full dataset
    features_before = extract_features(conn)

    # 2. Delete all activity occurring after day 14 for every user
    cursor = conn.cursor()

    # Delete trades after day 14
    cursor.execute("""
        DELETE FROM trades
        WHERE trade_date > (
            SELECT date(u.signup_date, '+14 days')
            FROM users u
            WHERE u.user_id = trades.user_id
        );
    """)

    # Delete sessions after day 14
    cursor.execute("""
        DELETE FROM sessions
        WHERE session_date > (
            SELECT date(u.signup_date, '+14 days')
            FROM users u
            WHERE u.user_id = sessions.user_id
        );
    """)

    # Delete funding after day 14
    cursor.execute("""
        DELETE FROM funding
        WHERE fund_date > (
            SELECT date(u.signup_date, '+14 days')
            FROM users u
            WHERE u.user_id = funding.user_id
        );
    """)

    # Delete support tickets after day 14
    cursor.execute("""
        DELETE FROM support_tickets
        WHERE ticket_date > (
            SELECT date(u.signup_date, '+14 days')
            FROM users u
            WHERE u.user_id = support_tickets.user_id
        );
    """)
    conn.commit()

    # 3. Extract features again on the pruned database
    features_after = extract_features(conn)
    conn.close()

    # 4. Assert that day-14 features are strictly identical
    pd.testing.assert_frame_equal(
        features_before,
        features_after,
        check_dtype=True,
        check_exact=True,
        obj="Day-14 feature extraction comparison (before vs after deleting post-day-14 activity)",
    )


def test_day14_feature_leakage_injection(test_db_copy: Path):
    """Assert that injecting massive activity after day 14 does not alter day-14 features."""
    conn = sqlite3.connect(test_db_copy)
    features_before = extract_features(conn)

    cursor = conn.cursor()
    # Inject massive trade and session activity on day 30 and day 75 for user 1
    cursor.execute("""
        INSERT INTO trades (user_id, trade_date, product, value, realized_pnl)
        VALUES (1, '2025-12-30', 'futures', 500000.0, -50000.0);
    """)
    cursor.execute("""
        INSERT INTO sessions (user_id, session_date, screens_viewed, watchlist_adds)
        VALUES (1, '2025-12-30', 100, 50);
    """)
    conn.commit()

    features_after = extract_features(conn)
    conn.close()

    pd.testing.assert_frame_equal(
        features_before,
        features_after,
        check_dtype=True,
        check_exact=True,
        obj="Day-14 feature extraction comparison (before vs after injecting post-day-14 activity)",
    )
