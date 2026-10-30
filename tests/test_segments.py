"""Tests for rule-based user segmentation and expected value calculation."""

import pandas as pd
import pytest

from src.segments import assign_segment, apply_segments_and_playbook


def test_segment_rules():
    """Verify segment assignment for edge cases."""
    # Burned: traded and worst trade P&L <= -250
    burned_user = pd.Series({
        "trade_count_d14": 2,
        "worst_trade_pnl_d14": -300.0,
        "is_funded_d14": 1,
        "total_watchlist_adds_d14": 4,
    })
    assert assign_segment(burned_user) == "Burned"

    # Hesitant: funded, no trade
    hesitant_user = pd.Series({
        "trade_count_d14": 0,
        "worst_trade_pnl_d14": 0.0,
        "is_funded_d14": 1,
        "total_watchlist_adds_d14": 2,
    })
    assert assign_segment(hesitant_user) == "Hesitant"

    # Browser: unfunded and 6+ watchlist adds
    browser_user = pd.Series({
        "trade_count_d14": 0,
        "worst_trade_pnl_d14": 0.0,
        "is_funded_d14": 0,
        "total_watchlist_adds_d14": 7,
    })
    assert assign_segment(browser_user) == "Browser"

    # Unfunded: not funded (and <6 watchlist adds)
    unfunded_user = pd.Series({
        "trade_count_d14": 0,
        "worst_trade_pnl_d14": 0.0,
        "is_funded_d14": 0,
        "total_watchlist_adds_d14": 3,
    })
    assert assign_segment(unfunded_user) == "Unfunded"

    # Monitor: funded, traded, worst P&L > -250
    monitor_user = pd.Series({
        "trade_count_d14": 3,
        "worst_trade_pnl_d14": -50.0,
        "is_funded_d14": 1,
        "total_watchlist_adds_d14": 5,
    })
    assert assign_segment(monitor_user) == "Monitor"


def test_expected_value_math_and_contact_condition():
    """Verify expected value = (risk * save_rate * LTV) - 15, and contact condition."""
    test_df = pd.DataFrame([
        {
            "user_id": 1,
            "trade_count_d14": 2,
            "worst_trade_pnl_d14": -500.0,
            "is_funded_d14": 1,
            "total_watchlist_adds_d14": 2,
            "predicted_risk": 0.50,  # Burned: save_rate 0.18, LTV 2200 -> 0.50*0.18*2200 - 15 = 198 - 15 = 183
        },
        {
            "user_id": 2,
            "trade_count_d14": 1,
            "worst_trade_pnl_d14": 100.0,
            "is_funded_d14": 1,
            "total_watchlist_adds_d14": 1,
            "predicted_risk": 0.01,  # Monitor: save_rate 0.04, LTV 1500 -> 0.01*0.04*1500 - 15 = 0.6 - 15 = -14.4
        },
    ])

    result = apply_segments_and_playbook(test_df)

    # User 1 should have positive EV and should_contact == True
    u1 = result.iloc[0]
    assert u1["segment"] == "Burned"
    assert u1["expected_value"] == 183.0
    assert u1["should_contact"] == True

    # User 2 should have negative EV and should_contact == False
    u2 = result.iloc[1]
    assert u2["segment"] == "Monitor"
    assert u2["expected_value"] == -14.4
    assert u2["should_contact"] == False
