"""Tests for model training outputs and scoring data."""

import json
from pathlib import Path
import pandas as pd
import pytest

from src.config import METRICS_PATH, SCORES_PATH, SEGMENT_PLAYBOOK


def test_scores_artifact_validity():
    """Verify that scores.csv exists and contains all required columns with valid ranges."""
    assert SCORES_PATH.exists(), f"scores.csv missing at {SCORES_PATH}"

    scores_df = pd.read_csv(SCORES_PATH)
    assert len(scores_df) == 20000, f"Expected 20,000 scores, found {len(scores_df)}"

    required_cols = [
        "user_id",
        "signup_date",
        "acquisition_channel",
        "is_dormant",
        "predicted_risk",
        "risk_decile",
        "segment",
        "recommended_action",
        "recommended_channel",
        "recommended_message",
        "save_rate",
        "lifetime_value",
        "expected_value",
        "should_contact",
        "top_reason_1",
    ]
    for col in required_cols:
        assert col in scores_df.columns, f"Missing required column: {col}"

    # Verify risk range
    assert scores_df["predicted_risk"].min() >= 0.0
    assert scores_df["predicted_risk"].max() <= 1.0

    # Verify valid segments
    valid_segments = set(SEGMENT_PLAYBOOK.keys())
    observed_segments = set(scores_df["segment"].unique())
    assert observed_segments.issubset(valid_segments)

    # Verify EV contact logic: contact ONLY if EV > 0
    contact_condition = scores_df["should_contact"] == (scores_df["expected_value"] > 0)
    assert contact_condition.all(), "should_contact mismatch with expected_value > 0"


def test_metrics_artifact_validity():
    """Verify that metrics.json contains required model evaluation metrics."""
    assert METRICS_PATH.exists(), f"metrics.json missing at {METRICS_PATH}"

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    for model_name in ["logistic_regression", "gradient_boosting"]:
        assert model_name in metrics["models"]
        m = metrics["models"][model_name]
        for metric_key in ["roc_auc", "pr_auc", "brier_score", "top_decile_capture", "top_decile_lift"]:
            assert metric_key in m, f"Missing {metric_key} in {model_name}"
            assert isinstance(m[metric_key], (int, float))

        # Check performance sanity (better than random guess)
        assert m["roc_auc"] > 0.60
        assert m["top_decile_lift"] > 1.2

    assert "caveats" in metrics and len(metrics["caveats"]) >= 3
    assert "feature_importances" in metrics and len(metrics["feature_importances"]) > 0
