"""Model and threshold view: Metrics, drivers, ROC curve, model comparison, and contact threshold optimizer."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from app.ui import (
    COLOR_BORDER,
    COLOR_GRIDLINE,
    COLOR_INK,
    COLOR_MUTED_INK,
    COLOR_MUTED_RED,
    COLOR_PETROL,
    COLOR_SURFACE,
    apply_chart_theme,
    format_rupees,
    render_callout,
    render_metric_strip,
    render_section_header,
)
from app.data import get_metrics, get_scores
from src.config import CONTACT_COST_INR


def render() -> None:
    render_section_header(
        "Model and threshold",
        "Hold-out evaluation metrics, permutation risk drivers, ROC curve, and economic threshold optimization.",
    )

    metrics_data = get_metrics()
    scores_df = get_scores()

    if not metrics_data or scores_df.empty:
        st.warning("Model metrics or scores unavailable. Please run the pipeline.")
        return

    gb_metrics = metrics_data["models"]["gradient_boosting"]
    lr_metrics = metrics_data["models"]["logistic_regression"]

    # 1. Ruled Metric Strip
    metrics = [
        {"label": "Hold-out ROC AUC", "value": f"{gb_metrics['roc_auc']:.4f}", "sub": "Chronological test set"},
        {"label": "Hold-out PR AUC", "value": f"{gb_metrics['pr_auc']:.4f}", "sub": "Precision-recall area"},
        {"label": "Brier calibration score", "value": f"{gb_metrics['brier_score']:.4f}", "sub": "Probability accuracy"},
        {"label": "Top-decile lift", "value": f"{gb_metrics['top_decile_lift']:.2f}x", "sub": "Over random selection"},
        {"label": "Top-decile capture", "value": f"{gb_metrics['top_decile_capture'] * 100:.1f}%", "sub": "Of all dormant users"},
    ]
    render_metric_strip(metrics)

    # 2. Model Comparison Table & ROC Curve (2-column layout)
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Model comparison on hold-out set</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Evaluated on signups on/after {metrics_data.get('split_date', '2025-10-01')} ({metrics_data.get('test_size', 0):,} users)</p>", unsafe_allow_html=True)

        comp_df = pd.DataFrame({
            "Metric": ["ROC AUC", "PR AUC", "Brier Score", "Top-Decile Capture", "Top-Decile Lift"],
            "Logistic Regression (Baseline)": [
                f"{lr_metrics['roc_auc']:.4f}",
                f"{lr_metrics['pr_auc']:.4f}",
                f"{lr_metrics['brier_score']:.4f}",
                f"{lr_metrics['top_decile_capture'] * 100:.1f}%",
                f"{lr_metrics['top_decile_lift']:.2f}x",
            ],
            "Gradient Boosting (HistGB)": [
                f"{gb_metrics['roc_auc']:.4f}",
                f"{gb_metrics['pr_auc']:.4f}",
                f"{gb_metrics['brier_score']:.4f}",
                f"{gb_metrics['top_decile_capture'] * 100:.1f}%",
                f"{gb_metrics['top_decile_lift']:.2f}x",
            ],
        })
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>ROC curve (Gradient Boosting)</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>True positive rate vs false positive rate across classification thresholds</p>", unsafe_allow_html=True)

        roc_pts = metrics_data.get("roc_curve_gb", [])
        if roc_pts:
            fpr = [p["fpr"] for p in roc_pts]
            tpr = [p["tpr"] for p in roc_pts]

            fig_roc = go.Figure()
            # Benchmark diagonal
            fig_roc.add_trace(
                go.Scatter(
                    x=[0, 1],
                    y=[0, 1],
                    mode="lines",
                    line=dict(color=COLOR_BORDER, dash="dash", width=1),
                    name="Random guess (AUC = 0.50)",
                )
            )
            # Model ROC
            fig_roc.add_trace(
                go.Scatter(
                    x=fpr,
                    y=tpr,
                    mode="lines",
                    line=dict(color=COLOR_PETROL, width=2),
                    name=f"Gradient Boosting (AUC = {gb_metrics['roc_auc']:.4f})",
                )
            )
            fig_roc.update_layout(
                xaxis=dict(title="False Positive Rate", range=[0, 1], showgrid=True),
                yaxis=dict(title="True Positive Rate", range=[0, 1], showgrid=True),
                margin=dict(l=10, r=10, t=10, b=20),
                height=260,
                showlegend=True,
            )
            apply_chart_theme(fig_roc, height=260)
            st.plotly_chart(fig_roc, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Permutation Feature Importance
    st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Top risk drivers (Permutation importance)</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Impact on model ROC AUC when each day-14 feature is randomly permuted</p>", unsafe_allow_html=True)

    importances = metrics_data.get("feature_importances", [])
    if importances:
        imp_df = pd.DataFrame(importances).head(8)
        imp_df = imp_df.sort_values(by="importance", ascending=True)

        fig_imp = go.Figure(
            go.Bar(
                y=imp_df["feature"],
                x=imp_df["importance"],
                orientation="h",
                marker=dict(color=COLOR_PETROL),
                text=[f"+{val:.4f}" for val in imp_df["importance"]],
                textposition="outside",
                textfont=dict(size=11, color=COLOR_INK),
            )
        )
        fig_imp.update_layout(
            xaxis=dict(title="Permutation Importance (AUC Drop)", showgrid=True),
            yaxis=dict(title=None),
            margin=dict(l=10, r=40, t=10, b=20),
            height=280,
        )
        apply_chart_theme(fig_imp, height=280)
        st.plotly_chart(fig_imp, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 4. Economic Contact Threshold Optimizer
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>Economic contact threshold optimizer</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 16px;'>Simulate contact cost and save rate assumptions to find the exact risk cutoff that maximizes portfolio Expected Value.</p>", unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1:
        cost_slider = st.slider("Contact cost per user (₹)", min_value=5.0, max_value=60.0, value=CONTACT_COST_INR, step=1.0)
    with s2:
        save_slider = st.slider("Blended save rate (%)", min_value=5.0, max_value=40.0, value=18.0, step=1.0)
    with s3:
        ltv_slider = st.slider("Blended customer LTV (₹)", min_value=500, max_value=3500, value=1500, step=100)

    # Compute optimal threshold curve across risk thresholds from 0.05 to 0.90
    sim_save_rate = save_slider / 100.0
    sim_ltv = float(ltv_slider)
    sim_cost = float(cost_slider)

    user_risks = scores_df["predicted_risk"].values
    threshold_range = np.linspace(0.05, 0.85, 41)

    curve_ev = []
    curve_volume = []
    for t in threshold_range:
        mask = user_risks >= t
        vol = int(np.sum(mask))
        if vol > 0:
            # Individual net return = (risk * save_rate * LTV) - cost
            net_return = np.sum((user_risks[mask] * sim_save_rate * sim_ltv) - sim_cost)
        else:
            net_return = 0.0
        curve_ev.append(net_return)
        curve_volume.append(vol)

    best_idx = int(np.argmax(curve_ev))
    best_threshold = threshold_range[best_idx]
    best_net_ev = curve_ev[best_idx]
    best_volume = curve_volume[best_idx]
    best_pct = (best_volume / len(scores_df)) * 100.0

    # Summary Metric Strip for Optimal Strategy
    opt_metrics = [
        {"label": "Optimal risk threshold", "value": f"{best_threshold * 100:.1f}%", "sub": "Cutoff for contact"},
        {"label": "Contact volume", "value": f"{best_volume:,}", "sub": f"{best_pct:.1f}% of cohort"},
        {"label": "Maximum net expected return", "value": format_rupees(best_net_ev, compact=True), "sub": f"At ₹{sim_cost:.0f} cost / user"},
        {"label": "Net EV per contacted user", "value": format_rupees(best_net_ev / best_volume) if best_volume > 0 else "₹0", "sub": "Per intervention"},
    ]
    render_metric_strip(opt_metrics)

    # Curve Chart
    fig_opt = go.Figure()
    fig_opt.add_trace(
        go.Scatter(
            x=[t * 100 for t in threshold_range],
            y=curve_ev,
            mode="lines",
            line=dict(color=COLOR_PETROL, width=2.5),
            name="Net Expected Return (₹)",
        )
    )
    # Highlight maximum
    fig_opt.add_trace(
        go.Scatter(
            x=[best_threshold * 100],
            y=[best_net_ev],
            mode="markers",
            marker=dict(color=COLOR_MUTED_RED, size=10, symbol="circle"),
            name=f"Peak: Cutoff {best_threshold * 100:.1f}% ({format_rupees(best_net_ev, compact=True)})",
        )
    )
    fig_opt.update_layout(
        xaxis=dict(title="Risk Cutoff Threshold (%)", showgrid=True),
        yaxis=dict(title="Net Expected Portfolio Value (₹)", showgrid=True),
        margin=dict(l=10, r=10, t=10, b=20),
        height=300,
        showlegend=True,
    )
    apply_chart_theme(fig_opt, height=300)
    st.plotly_chart(fig_opt, use_container_width=True, config={"displayModeBar": False})

    # Strategy callout
    render_callout(
        f"Threshold Strategy Recommendation: Intervene with users whose day-14 dormancy risk is {best_threshold * 100:.1f}% or higher. Contacting users below this threshold incurs more in contact cost (₹{sim_cost:.0f}) than their incremental retention value generates.",
        tone="neutral",
    )
