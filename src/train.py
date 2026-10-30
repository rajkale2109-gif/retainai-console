"""Model training, hold-out evaluation, out-of-fold scoring, and driver analysis."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.inspection import permutation_importance

from src.config import (
    DB_PATH,
    METRICS_PATH,
    PROCESSED_DATA_DIR,
    RANDOM_SEED,
    SCORES_PATH,
    TRAIN_TEST_SPLIT_DATE,
)
from src.features import (
    FEATURE_NAMES_MAP,
    load_raw_dataset,
    prepare_feature_matrix,
)
from src.segments import apply_segments_and_playbook


def compute_evaluation_metrics(y_true: np.ndarray, y_pred_proba: np.ndarray) -> Dict[str, float]:
    """Compute ROC AUC, PR AUC, Brier score, and top-decile capture and lift."""
    roc_auc = float(roc_auc_score(y_true, y_pred_proba))
    pr_auc = float(average_precision_score(y_true, y_pred_proba))
    brier = float(brier_score_loss(y_true, y_pred_proba))

    # Top-decile capture and lift
    n_samples = len(y_true)
    top_decile_size = max(1, int(np.ceil(0.10 * n_samples)))
    sorted_indices = np.argsort(y_pred_proba)[::-1]
    top_decile_indices = sorted_indices[:top_decile_size]

    total_positives = int(np.sum(y_true))
    positives_in_top_decile = int(np.sum(y_true[top_decile_indices]))

    top_decile_capture = (
        float(positives_in_top_decile / total_positives) if total_positives > 0 else 0.0
    )
    # Lift = capture / decile fraction (0.10)
    top_decile_lift = float(top_decile_capture / 0.10)

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "top_decile_capture": round(top_decile_capture, 4),
        "top_decile_lift": round(top_decile_lift, 2),
    }


def compute_permutation_importance(
    model: Any,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    feature_cols: List[str],
) -> List[Dict[str, Any]]:
    """Compute permutation feature importance with plain-language feature names."""
    perm_res = permutation_importance(
        model,
        X_test,
        y_test,
        n_repeats=5,
        random_state=RANDOM_SEED,
        scoring="roc_auc",
    )

    importances = []
    for col, mean_imp, std_imp in zip(
        feature_cols, perm_res.importances_mean, perm_res.importances_std
    ):
        # Map raw or one-hot column back to plain-language descriptor
        clean_name = FEATURE_NAMES_MAP.get(col, col)
        if clean_name == col:
            for prefix_candidate in ["acquisition_channel", "city_tier", "age_band"]:
                if col.startswith(prefix_candidate + "_"):
                    val = col[len(prefix_candidate) + 1:].replace("_", " ").title()
                    clean_name = f"{FEATURE_NAMES_MAP[prefix_candidate]}: {val}"
                    break

        importances.append({
            "raw_feature": col,
            "feature": clean_name,
            "importance": round(float(mean_imp), 4),
            "std": round(float(std_imp), 4),
        })

    importances.sort(key=lambda x: x["importance"], reverse=True)
    return importances


def generate_oof_predictions(
    X: pd.DataFrame,
    y: np.ndarray,
) -> np.ndarray:
    """Generate 5-fold stratified out-of-fold risk predictions for every user."""
    oof_preds = np.zeros(len(y), dtype=float)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    for train_idx, val_idx in skf.split(X, y):
        X_tr, y_tr = X.iloc[train_idx], y[train_idx]
        X_val = X.iloc[val_idx]

        model = HistGradientBoostingClassifier(
            max_iter=120,
            learning_rate=0.08,
            max_leaf_nodes=31,
            random_state=RANDOM_SEED,
        )
        model.fit(X_tr, y_tr)
        oof_preds[val_idx] = model.predict_proba(X_val)[:, 1]

    return oof_preds


def assign_user_drivers(row: pd.Series) -> Tuple[str, str, str]:
    """Generate 3 plain-language reasons for a user's risk score."""
    reasons = []

    # Check key drivers
    if row.get("is_funded_d14", 0) == 0:
        reasons.append("Account remains unfunded after 14 days")
    if row.get("worst_trade_pnl_d14", 0.0) <= -250.0:
        reasons.append(f"Incurred early trading loss of ₹{abs(row.get('worst_trade_pnl_d14', 0.0)):,.0f}")
    if row.get("acquisition_channel") == "influencer":
        reasons.append("High-churn acquisition source (influencer campaign)")
    if row.get("session_count_d14", 0) <= 1:
        reasons.append("Minimal app engagement (only 1 session in first 14 days)")
    if row.get("kyc_completed_d14", 0) == 0:
        reasons.append("KYC verification incomplete")
    if row.get("trade_count_d14", 0) == 0 and row.get("is_funded_d14", 0) == 1:
        reasons.append("Account funded but zero trades executed")
    if row.get("total_watchlist_adds_d14", 0) >= 6 and row.get("is_funded_d14", 0) == 0:
        reasons.append("High browsing intent with 6+ watchlist additions")

    # Fallbacks for low-risk active profiles
    if len(reasons) < 3:
        if row.get("trade_count_d14", 0) > 0 and row.get("worst_trade_pnl_d14", 0.0) > 0:
            reasons.append("Profitable initial trades executed")
        if row.get("session_count_d14", 0) >= 4:
            reasons.append("Frequent multi-day app logins")
        if row.get("acquisition_channel") in ["referral", "organic"]:
            reasons.append("High-intent acquisition channel")

    while len(reasons) < 3:
        reasons.append("Standard onboarding lifecycle activity")

    return reasons[0], reasons[1], reasons[2]


def train_and_evaluate(
    conn: sqlite3.Connection,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Run full training pipeline, metrics evaluation, and user scoring."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    features_raw, labels_raw = load_raw_dataset(conn)
    df_merged = features_raw.merge(labels_raw, on="user_id", how="inner")

    # 2. Encode features
    encoded_df, feature_cols = prepare_feature_matrix(df_merged)

    # 3. Time-based train/test split: signups before 2025-10-01 train, later test
    train_mask = df_merged["signup_date"] < TRAIN_TEST_SPLIT_DATE
    test_mask = ~train_mask

    X_train = encoded_df.loc[train_mask, feature_cols]
    y_train = df_merged.loc[train_mask, "is_dormant"].values

    X_test = encoded_df.loc[test_mask, feature_cols]
    y_test = df_merged.loc[test_mask, "is_dormant"].values

    print(f"Train users: {len(X_train):,} (signups < {TRAIN_TEST_SPLIT_DATE})")
    print(f"Test users : {len(X_test):,} (signups >= {TRAIN_TEST_SPLIT_DATE})")

    # 4. Baseline Model: Logistic Regression with standard scaling
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)),
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_test_preds = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_metrics = compute_evaluation_metrics(y_test, lr_test_preds)

    # 5. Main Model: Gradient Boosting (HistGradientBoostingClassifier)
    gb_model = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.08,
        max_leaf_nodes=31,
        random_state=RANDOM_SEED,
    )
    gb_model.fit(X_train, y_train)
    gb_test_preds = gb_model.predict_proba(X_test)[:, 1]
    gb_metrics = compute_evaluation_metrics(y_test, gb_test_preds)

    # Compute ROC Curve points for Plotly visualization
    fpr, tpr, roc_thresholds = roc_curve(y_test, gb_test_preds)
    # Downsample points for efficient JSON storage
    indices = np.linspace(0, len(fpr) - 1, min(100, len(fpr))).astype(int)
    roc_points = [
        {"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)}
        for i in indices
    ]

    # 6. Permutation Importance
    importance_list = compute_permutation_importance(gb_model, X_test, y_test, feature_cols)

    # 7. 5-fold Out-Of-Fold (OOF) Risk Predictions for EVERY user
    print("Generating 5-fold out-of-fold risk scores for all 20,000 users...")
    oof_risks = generate_oof_predictions(encoded_df[feature_cols], df_merged["is_dormant"].values)
    df_merged["predicted_risk"] = np.round(oof_risks, 4)

    # Compute risk deciles (1 = lowest risk, 10 = highest risk)
    df_merged["risk_decile"] = pd.qcut(
        df_merged["predicted_risk"], q=10, labels=False, duplicates="drop"
    ) + 1

    # 8. Segments, Interventions, and Expected Value
    scores_df = apply_segments_and_playbook(df_merged, risk_col="predicted_risk")

    # Assign plain-language drivers
    reasons = scores_df.apply(assign_user_drivers, axis=1)
    scores_df["top_reason_1"] = [r[0] for r in reasons]
    scores_df["top_reason_2"] = [r[1] for r in reasons]
    scores_df["top_reason_3"] = [r[2] for r in reasons]

    # Select final score columns
    output_cols = [
        "user_id",
        "signup_date",
        "acquisition_channel",
        "city_tier",
        "age_band",
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
        "top_reason_2",
        "top_reason_3",
    ]
    final_scores = scores_df[output_cols].copy()
    final_scores.to_csv(SCORES_PATH, index=False)
    print(f"Saved scores to {SCORES_PATH}")

    # 9. Honest Data Science Limitations and Caveats
    caveats = [
        "Synthetic Data: Calibrated on synthetic distributions; real retail broking user behaviour may feature seasonal market volatility and non-linear macroeconomic shocks.",
        "Correlation vs. Causation: Model risk scores quantify churn correlation. An intervention will only yield net return if the identified drivers are causally responsive to the recommended action.",
        "Assumed Save Rates & LTV: Segment save rates and lifetime values are operational assumptions. Real campaign performance must be calibrated through controlled A/B experiments.",
        "Day-14 Blind Spot: Features strictly ignore post-day-14 behaviour to prevent leakage. Sudden user life events or sharp portfolio drawdowns occurring on day 25 or 40 are invisible to this predictor.",
        "Static Contact Cost: Contact cost is fixed at ₹15 per user; real blended contact costs vary significantly between automated SMS/WhatsApp nudges and human relationship manager phone calls.",
    ]

    metrics_payload = {
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "split_date": TRAIN_TEST_SPLIT_DATE,
        "models": {
            "logistic_regression": lr_metrics,
            "gradient_boosting": gb_metrics,
        },
        "roc_curve_gb": roc_points,
        "feature_importances": importance_list[:10],
        "caveats": caveats,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"Saved metrics to {METRICS_PATH}")

    return metrics_payload, final_scores


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    metrics, scores = train_and_evaluate(conn)
    conn.close()

    print("\n" + "=" * 60)
    print("STAGE 3 MODEL EVALUATION REPORT")
    print("=" * 60)
    print(f"Train signups (< {metrics['split_date']}): {metrics['train_size']:,}")
    print(f"Test signups  (>= {metrics['split_date']}): {metrics['test_size']:,}")
    print("\nModel Comparison on Hold-out Test Set:")
    print(f"{'Metric':<22} | {'Logistic Regression':<20} | {'Gradient Boosting':<20}")
    print("-" * 68)
    for k in ["roc_auc", "pr_auc", "brier_score", "top_decile_capture", "top_decile_lift"]:
        lr_v = metrics["models"]["logistic_regression"][k]
        gb_v = metrics["models"]["gradient_boosting"][k]
        print(f"{k:<22} | {lr_v:<20} | {gb_v:<20}")

    print("\nTop 5 Risk Drivers (Permutation Importance):")
    for idx, item in enumerate(metrics["feature_importances"][:5], 1):
        print(f"  {idx}. {item['feature']:<35} (Score: {item['importance']:+.4f})")

    print("\nModel Limitations & Caveats:")
    for c in metrics["caveats"]:
        print(f"  * {c}")
    print("=" * 60)
