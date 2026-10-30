"""Authoritative economics engine for RetainAI.

Single source of truth for:
- Contact cost (default: ₹15.0)
- Segment unit economics (save rate, lifetime value)
- Net Expected Value: EV = (risk * save_rate * LTV) - contact_cost
- Segment break-even risk thresholds: R* = cost / (save_rate * LTV)
- Capacity-constrained threshold optimization
"""

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

from src.config import CONTACT_COST_INR, SEGMENT_PLAYBOOK, SegmentDef


def get_segment_playbook() -> Dict[str, SegmentDef]:
    """Return authoritative segment playbook definitions."""
    return SEGMENT_PLAYBOOK


def get_segment_economics(segment: str) -> Dict[str, Any]:
    """Return economic parameters for a specific segment."""
    pbook = SEGMENT_PLAYBOOK.get(segment)
    if not pbook:
        return {"save_rate": 0.10, "lifetime_value": 1000.0, "channel": "In-app"}
    return {
        "save_rate": pbook.save_rate,
        "lifetime_value": pbook.lifetime_value,
        "action": pbook.action,
        "channel": pbook.channel,
        "message": pbook.message,
    }


def calculate_expected_value(
    risk: float,
    segment: str,
    contact_cost: float = CONTACT_COST_INR,
    save_rate_multiplier: float = 1.0,
) -> float:
    """Calculate net expected value for an individual user."""
    econ = get_segment_economics(segment)
    effective_save_rate = min(1.0, econ["save_rate"] * save_rate_multiplier)
    ev = (risk * effective_save_rate * econ["lifetime_value"]) - contact_cost
    return float(np.round(ev, 2))


def break_even_risk(
    segment: str,
    contact_cost: float = CONTACT_COST_INR,
    save_rate_multiplier: float = 1.0,
) -> float:
    """Calculate the minimum risk probability required for net positive return in a segment."""
    econ = get_segment_economics(segment)
    effective_save_rate = min(1.0, econ["save_rate"] * save_rate_multiplier)
    denom = effective_save_rate * econ["lifetime_value"]
    if denom <= 0:
        return 1.0
    return float(np.clip(contact_cost / denom, 0.0, 1.0))


def compute_portfolio_economics(
    df: pd.DataFrame,
    threshold: float = 0.0,
    contact_cost: float = CONTACT_COST_INR,
    save_rate_multiplier: float = 1.0,
    capacity: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate total and marginal portfolio economics using user-level segment parameters.
    
    Guarantees that metrics match exactly across all views.
    """
    if df.empty:
        return {
            "total_users": 0,
            "contacted_users": 0,
            "total_net_ev": 0.0,
            "avg_ev_per_contact": 0.0,
            "marginal_ev": 0.0,
            "cutoff_used": threshold,
        }

    # Compute EV for all rows under the requested contact_cost and save_rate_multiplier
    save_rates = np.array([get_segment_economics(s)["save_rate"] for s in df["segment"]]) * save_rate_multiplier
    save_rates = np.clip(save_rates, 0.0, 1.0)
    ltvs = np.array([get_segment_economics(s)["lifetime_value"] for s in df["segment"]])
    risks = df["predicted_risk"].values

    net_evs = (risks * save_rates * ltvs) - contact_cost

    # Filter by risk threshold
    mask = risks >= threshold
    qualifying_indices = np.where(mask)[0]

    # Sort qualifying users by EV descending
    sorted_order = qualifying_indices[np.argsort(-net_evs[qualifying_indices])]

    # Apply operational capacity ceiling if specified
    if capacity is not None and capacity > 0 and len(sorted_order) > capacity:
        contacted_indices = sorted_order[:capacity]
    else:
        contacted_indices = sorted_order

    contacted_count = len(contacted_indices)
    total_net_ev = float(np.sum(net_evs[contacted_indices])) if contacted_count > 0 else 0.0
    avg_ev = (total_net_ev / contacted_count) if contacted_count > 0 else 0.0
    marginal_ev = float(net_evs[contacted_indices[-1]]) if contacted_count > 0 else 0.0

    return {
        "total_users": len(df),
        "contacted_users": contacted_count,
        "total_net_ev": float(np.round(total_net_ev, 2)),
        "avg_ev_per_contact": float(np.round(avg_ev, 2)),
        "marginal_ev": float(np.round(marginal_ev, 2)),
        "cutoff_used": float(threshold),
    }
