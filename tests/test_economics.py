"""Test suite for the authoritative economics module."""

import pytest
import pandas as pd
from src.economics import (
    calculate_expected_value,
    break_even_risk,
    compute_portfolio_economics,
    get_segment_economics,
    CONTACT_COST_INR,
)
from src.config import SCORES_PATH


def test_segment_economics_lookup():
    """Verify segment economics return valid numbers."""
    hesitant = get_segment_economics("Hesitant")
    assert hesitant["save_rate"] == 0.24
    assert hesitant["lifetime_value"] == 1800.0


def test_expected_value_formula():
    """Verify EV = (risk * save_rate * LTV) - contact_cost."""
    # Hesitant user with 50% risk:
    # 0.50 * 0.24 * 1800 - 15 = 216 - 15 = 201
    ev = calculate_expected_value(risk=0.50, segment="Hesitant", contact_cost=15.0)
    assert ev == 201.0

    # Low risk user with negative return:
    # 0.01 * 0.08 * 800 - 15 = 0.64 - 15 = -14.36
    ev_neg = calculate_expected_value(risk=0.01, segment="Unfunded", contact_cost=15.0)
    assert ev_neg == -14.36


def test_break_even_risk():
    """Verify break-even calculation R* = cost / (save_rate * LTV)."""
    # Hesitant: 15 / (0.24 * 1800) = 15 / 432 = 0.03472
    be = break_even_risk("Hesitant", contact_cost=15.0)
    assert 0.034 < be < 0.035


def test_portfolio_economics_consistency():
    """Assert that scores.csv portfolio economics are internally consistent."""
    if not SCORES_PATH.exists():
        pytest.skip("scores.csv not found")

    scores_df = pd.read_csv(SCORES_PATH)
    res = compute_portfolio_economics(scores_df, threshold=0.0, contact_cost=15.0)

    # Sum of expected_value column in scores.csv
    direct_sum = scores_df["expected_value"].sum()
    assert abs(res["total_net_ev"] - direct_sum) < 5.0  # within rounding bounds

    # Contactable only:
    contactable_df = scores_df[scores_df["should_contact"]]
    res_pos = compute_portfolio_economics(scores_df[scores_df["should_contact"]], threshold=0.0, contact_cost=15.0)
    assert abs(res_pos["total_net_ev"] - contactable_df["expected_value"].sum()) < 5.0
