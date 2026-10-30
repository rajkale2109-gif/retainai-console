"""Deterministic business segment classification and expected value calculation.

Segments (Rules from SPEC.md):
- Burned: Traded and worst trade P&L <= -250.
- Hesitant: Funded, no trade.
- Browser: Unfunded and 6+ watchlist adds.
- Unfunded: Not funded (< 6 watchlist adds).
- Monitor: Everything else.

Unit Economics:
- Expected Value = risk * save_rate * lifetime_value - 15.0 (contact cost).
- Contact only users with positive net expected value (EV > 0).
"""

from typing import Dict, Tuple
import pandas as pd
import numpy as np

from src.config import CONTACT_COST_INR, SEGMENT_PLAYBOOK, SegmentDef


def assign_segment(row: pd.Series) -> str:
    """Classify a user into a segment based strictly on day-14 behavioural rules."""
    trade_count = row.get("trade_count_d14", 0)
    worst_pnl = row.get("worst_trade_pnl_d14", 0.0)
    is_funded = row.get("is_funded_d14", 0)
    watchlist_adds = row.get("total_watchlist_adds_d14", 0)

    # 1. Burned: traded and worst trade P&L <= -250
    if trade_count > 0 and worst_pnl <= -250.0:
        return "Burned"

    # 2. Hesitant: funded, no trade
    if is_funded == 1 and trade_count == 0:
        return "Hesitant"

    # 3. Browser: unfunded and 6+ watchlist adds
    if is_funded == 0 and watchlist_adds >= 6:
        return "Browser"

    # 4. Unfunded: not funded
    if is_funded == 0:
        return "Unfunded"

    # 5. Monitor: everything else (e.g. funded, active traders without major loss)
    return "Monitor"


def apply_segments_and_playbook(
    df: pd.DataFrame,
    risk_col: str = "predicted_risk",
    contact_cost: float = CONTACT_COST_INR,
) -> pd.DataFrame:
    """Assign segments, recommended playbook interventions, and compute Expected Value."""
    result = df.copy()

    # Determine segment for each user
    segments = result.apply(assign_segment, axis=1)
    result["segment"] = segments

    # Map playbook parameters
    result["recommended_action"] = [SEGMENT_PLAYBOOK[s].action for s in segments]
    result["recommended_channel"] = [SEGMENT_PLAYBOOK[s].channel for s in segments]
    result["recommended_message"] = [SEGMENT_PLAYBOOK[s].message for s in segments]
    result["save_rate"] = [SEGMENT_PLAYBOOK[s].save_rate for s in segments]
    result["lifetime_value"] = [SEGMENT_PLAYBOOK[s].lifetime_value for s in segments]

    # Compute Expected Value (EV)
    # Expected value = risk * save_rate * lifetime_value - contact_cost
    risks = result[risk_col].values if risk_col in result.columns else np.zeros(len(result))
    save_rates = result["save_rate"].values
    ltvs = result["lifetime_value"].values

    ev = (risks * save_rates * ltvs) - contact_cost
    result["expected_value"] = np.round(ev, 2)

    # Contact only users with positive net expected value
    result["should_contact"] = result["expected_value"] > 0.0

    return result


def compute_segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Generate high-level segment portfolio metrics for PM review."""
    summary_rows = []
    total_users = len(df)

    for seg_name, pbook in SEGMENT_PLAYBOOK.items():
        sub = df[df["segment"] == seg_name]
        cnt = len(sub)
        pct = (cnt / total_users * 100.0) if total_users > 0 else 0.0
        avg_risk = sub["predicted_risk"].mean() if "predicted_risk" in sub.columns and cnt > 0 else 0.0
        tot_ev = sub["expected_value"].sum() if "expected_value" in sub.columns and cnt > 0 else 0.0
        avg_ev = sub["expected_value"].mean() if "expected_value" in sub.columns and cnt > 0 else 0.0
        contactable = sub["should_contact"].sum() if "should_contact" in sub.columns else 0

        summary_rows.append({
            "segment": seg_name,
            "user_count": cnt,
            "user_pct": round(pct, 1),
            "avg_risk": round(avg_risk, 3),
            "save_rate": pbook.save_rate,
            "lifetime_value": pbook.lifetime_value,
            "channel": pbook.channel,
            "action": pbook.action,
            "total_expected_value": round(tot_ev, 2),
            "avg_expected_value": round(avg_ev, 2),
            "contactable_users": contactable,
        })

    return pd.DataFrame(summary_rows)
