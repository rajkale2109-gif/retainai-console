"""Model and threshold view: Hold-out metrics, aggregated feature importance, ROC/Calibration/Gain curves, and capacity-constrained threshold optimization."""

from typing import Dict, Any, List
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from app.ui import (
    get_current_theme,
    apply_chart_theme,
    format_rupees,
    render_metric_strip,
    render_section_header,
    render_tag,
    render_callout,
)
from app.data import get_metrics, get_scores
from src.config import CONTACT_COST_INR
from src.economics import get_segment_playbook, break_even_risk


def render() -> None:
    t = get_current_theme()

    render_section_header(
        "Model and threshold",
        "Hold-out evaluation metrics, permutation risk drivers, diagnostic curves, and capacity-constrained economic optimization.",
    )

    metrics_data = get_metrics()
    scores_df = get_scores()

    if not metrics_data or scores_df.empty:
        st.warning("Model metrics or scores unavailable. Please verify pipeline outputs.")
        return

    gb_metrics = metrics_data["models"]["gradient_boosting"]
    lr_metrics = metrics_data["models"]["logistic_regression"]

    # 1. Authoritative Metric Strip (Strictly 3 decimals for probability metrics)
    metrics = [
        {"label": "Hold-out ROC AUC", "value": f"{gb_metrics['roc_auc']:.3f}", "sub": f"Baseline LR: {lr_metrics['roc_auc']:.3f}", "delta": f"+{gb_metrics['roc_auc'] - lr_metrics['roc_auc']:.3f}", "delta_good": True},
        {"label": "Precision-Recall AUC", "value": f"{gb_metrics['pr_auc']:.3f}", "sub": f"Baseline LR: {lr_metrics['pr_auc']:.3f}", "delta": f"+{gb_metrics['pr_auc'] - lr_metrics['pr_auc']:.3f}", "delta_good": True},
        {"label": "Brier calibration score", "value": f"{gb_metrics['brier_score']:.3f}", "sub": f"Baseline LR: {lr_metrics['brier_score']:.3f}", "delta": f"{gb_metrics['brier_score'] - lr_metrics['brier_score']:.3f}", "delta_good": True},
        {"label": "Top-decile lift", "value": f"{gb_metrics['top_decile_lift']:.2f}x", "sub": "Over random selection", "delta": f"+{gb_metrics['top_decile_lift'] - lr_metrics['top_decile_lift']:.2f}x", "delta_good": True},
        {"label": "Top-decile capture", "value": f"{gb_metrics['top_decile_capture'] * 100:.1f}%", "sub": "Of all dormant investors", "delta": f"+{(gb_metrics['top_decile_capture'] - lr_metrics['top_decile_capture']) * 100:.1f} pts", "delta_good": True},
    ]
    render_metric_strip(metrics)

    # 2. Model Comparison Table & Feature Importance (Aggregated Channels)
    col_comp, col_imp = st.columns([1.0, 1.0], gap="medium")

    with col_comp:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Model comparison on chronological hold-out</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Signups &ge; {metrics_data.get("split_date", "2025-10-01")} ({metrics_data.get("test_size", 0):,} investors) with winning model highlighted</div>'
        )

        comp_data = [
            {
                "Evaluation Metric": "ROC AUC",
                "Logistic Regression (Baseline)": f"{lr_metrics['roc_auc']:.3f}",
                "Gradient Boosting (HistGB)": f"{gb_metrics['roc_auc']:.3f}",
                "Delta / Superiority": f"+{gb_metrics['roc_auc'] - lr_metrics['roc_auc']:.3f} (GB Win)",
            },
            {
                "Evaluation Metric": "PR AUC",
                "Logistic Regression (Baseline)": f"{lr_metrics['pr_auc']:.3f}",
                "Gradient Boosting (HistGB)": f"{gb_metrics['pr_auc']:.3f}",
                "Delta / Superiority": f"+{gb_metrics['pr_auc'] - lr_metrics['pr_auc']:.3f} (GB Win)",
            },
            {
                "Evaluation Metric": "Brier Calibration Score",
                "Logistic Regression (Baseline)": f"{lr_metrics['brier_score']:.3f}",
                "Gradient Boosting (HistGB)": f"{gb_metrics['brier_score']:.3f}",
                "Delta / Superiority": f"{gb_metrics['brier_score'] - lr_metrics['brier_score']:.3f} (Lower is better)",
            },
            {
                "Evaluation Metric": "Top-Decile Capture Rate",
                "Logistic Regression (Baseline)": f"{lr_metrics['top_decile_capture'] * 100:.1f}%",
                "Gradient Boosting (HistGB)": f"{gb_metrics['top_decile_capture'] * 100:.1f}%",
                "Delta / Superiority": f"+{(gb_metrics['top_decile_capture'] - lr_metrics['top_decile_capture']) * 100:.1f} pts",
            },
            {
                "Evaluation Metric": "Top-Decile Concentration Lift",
                "Logistic Regression (Baseline)": f"{lr_metrics['top_decile_lift']:.2f}x",
                "Gradient Boosting (HistGB)": f"{gb_metrics['top_decile_lift']:.2f}x",
                "Delta / Superiority": f"+{gb_metrics['top_decile_lift'] - lr_metrics['top_decile_lift']:.2f}x",
            },
        ]
        comp_df = pd.DataFrame(comp_data)
        st.dataframe(
            comp_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Evaluation Metric": st.column_config.TextColumn("Evaluation Metric", width="medium"),
                "Logistic Regression (Baseline)": st.column_config.TextColumn("Logistic Regression (Baseline)", width="small"),
                "Gradient Boosting (HistGB)": st.column_config.TextColumn("★ Gradient Boosting (HistGB)", width="small"),
                "Delta / Superiority": st.column_config.TextColumn("Delta / Superiority", width="medium"),
            },
        )

    with col_imp:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Permutation feature importance (Aggregated channels)</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">One-hot acquisition channels aggregated into root Acquisition Channel</div>'
        )

        importances = metrics_data.get("feature_importances", [])
        if importances:
            # Aggregate one-hot channel features back to root "Acquisition Channel"
            agg_dict: Dict[str, float] = {}
            for item in importances:
                feat = item["feature"]
                val = item["importance"]
                if feat.startswith("Acquisition channel:"):
                    feat_clean = "Acquisition Channel"
                else:
                    feat_clean = feat
                agg_dict[feat_clean] = agg_dict.get(feat_clean, 0.0) + val

            agg_list = [{"feature": k, "importance": v} for k, v in agg_dict.items()]
            agg_df = pd.DataFrame(agg_list).sort_values(by="importance", ascending=True)
            agg_max = float(agg_df["importance"].max()) * 1.30

            fig_imp = go.Figure(
                go.Bar(
                    y=agg_df["feature"],
                    x=agg_df["importance"],
                    orientation="h",
                    marker=dict(color=t.accent),
                    text=[f"+{val:.3f}" for val in agg_df["importance"]],
                    textposition="outside",
                    textfont=dict(size=11, color=t.text_primary, family="IBM Plex Mono"),
                    cliponaxis=False,
                )
            )
            fig_imp.update_layout(
                xaxis=dict(title="AUC Drop When Permuted", showgrid=True, zeroline=False, range=[0, agg_max]),
                yaxis=dict(title=None, tickfont=dict(size=11, color=t.text_primary)),
                margin=dict(l=10, r=60, t=10, b=20),
                height=240,
            )
            apply_chart_theme(fig_imp, height=240)
            st.plotly_chart(fig_imp, width="stretch", config={"displayModeBar": False})

    st.html("<div style='height: 12px;'></div>")

    # 3. Diagnostic Plots: ROC Curve, Decile Calibration, Cumulative Gain
    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Model diagnostic workbench</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Three rigorous diagnostic checks: ROC curve, decile probability calibration, and cumulative gain</div>'
    )

    tab_roc, tab_calib, tab_gain = st.tabs(["ROC Curve", "Decile Calibration Plot", "Cumulative Gain Chart"])

    with tab_roc:
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
                    line=dict(color=t.border, dash="dash", width=1.5),
                    name="Random Guess (AUC = 0.500)",
                )
            )
            # HistGB ROC
            fig_roc.add_trace(
                go.Scatter(
                    x=fpr,
                    y=tpr,
                    mode="lines",
                    line=dict(color=t.accent, width=2.5),
                    name=f"Gradient Boosting (AUC = {gb_metrics['roc_auc']:.3f})",
                    hovertemplate="FPR: %{x:.3f}<br>TPR: %{y:.3f}<extra></extra>",
                )
            )
            fig_roc.update_layout(
                xaxis=dict(title="False Positive Rate (1 - Specificity)", range=[0, 1], showgrid=True),
                yaxis=dict(title="True Positive Rate (Sensitivity / Recall)", range=[0, 1], showgrid=True),
                margin=dict(l=65, r=20, t=15, b=25),
                height=290,
                showlegend=True,
                legend=dict(x=0.03, y=0.97, bgcolor="rgba(0,0,0,0)"),
            )
            apply_chart_theme(fig_roc, height=290)
            st.plotly_chart(fig_roc, width="stretch", config={"displayModeBar": False})

    with tab_calib:
        # Decile calibration computation
        df_cal = scores_df.copy()
        df_cal["risk_bucket"] = pd.qcut(df_cal["predicted_risk"], q=10, labels=False, duplicates="drop")
        calib_stats = df_cal.groupby("risk_bucket").agg(
            mean_pred=("predicted_risk", "mean"),
            mean_actual=("is_dormant", "mean"),
            count=("user_id", "count"),
        ).reset_index()

        fig_cal = go.Figure()
        # 45-degree ideal calibration line
        fig_cal.add_trace(
            go.Scatter(
                x=[0, 0.8],
                y=[0, 0.8],
                mode="lines",
                line=dict(color=t.border, dash="dash", width=1.5),
                name="Perfect Calibration (y = x)",
            )
        )
        # Empirical decile points
        fig_cal.add_trace(
            go.Scatter(
                x=calib_stats["mean_pred"] * 100.0,
                y=calib_stats["mean_actual"] * 100.0,
                mode="lines+markers",
                line=dict(color=t.positive, width=2),
                marker=dict(size=8, symbol="circle", color=t.positive),
                name="Observed Deciles (HistGB)",
                hovertemplate="Predicted Risk: %{x:.1f}%<br>Observed Dormancy: %{y:.1f}%<extra></extra>",
            )
        )
        fig_cal.update_layout(
            xaxis=dict(title="Mean Predicted Risk (%)", showgrid=True),
            yaxis=dict(title="Observed Dormancy Rate (%)", showgrid=True),
            margin=dict(l=65, r=20, t=15, b=25),
            height=290,
            showlegend=True,
            legend=dict(x=0.03, y=0.97, bgcolor="rgba(0,0,0,0)"),
        )
        apply_chart_theme(fig_cal, height=290)
        st.plotly_chart(fig_cal, width="stretch", config={"displayModeBar": False})

    with tab_gain:
        # Cumulative gain curve computation
        df_gain = scores_df.sort_values(by="predicted_risk", ascending=False).reset_index(drop=True)
        tot_dormants = int(df_gain["is_dormant"].sum())
        df_gain["cum_dormant"] = df_gain["is_dormant"].cumsum()
        
        # Sample points every 2% to render fast, smooth chart
        pct_points = np.linspace(0.02, 1.0, 50)
        gain_x = []
        gain_y = []
        for p in pct_points:
            idx = int(p * len(df_gain)) - 1
            gain_x.append(p * 100.0)
            gain_y.append((df_gain.iloc[idx]["cum_dormant"] / tot_dormants) * 100.0)

        fig_gain = go.Figure()
        # Random selection diagonal
        fig_gain.add_trace(
            go.Scatter(
                x=[0, 100],
                y=[0, 100],
                mode="lines",
                line=dict(color=t.border, dash="dash", width=1.5),
                name="Random Selection (1:1 Gain)",
            )
        )
        # Model cumulative gain curve
        fig_gain.add_trace(
            go.Scatter(
                x=gain_x,
                y=gain_y,
                mode="lines",
                line=dict(color=t.accent, width=2.5),
                name=f"HistGB Model (Top 10% Captures {gb_metrics['top_decile_capture']*100:.1f}%)",
                hovertemplate="Population Contacted: %{x:.1f}%<br>Dormant Users Captured: %{y:.1f}%<extra></extra>",
            )
        )
        # Marker at 10%
        top10_y = (df_gain.iloc[int(0.10 * len(df_gain)) - 1]["cum_dormant"] / tot_dormants) * 100.0
        fig_gain.add_trace(
            go.Scatter(
                x=[10.0],
                y=[top10_y],
                mode="markers+text",
                marker=dict(color=t.warning, size=9),
                text=[f" Top 10% ({top10_y:.1f}%)"],
                textposition="top left",
                textfont=dict(size=11, color=t.text_primary, family="IBM Plex Mono"),
                name="Top Decile Point",
            )
        )
        fig_gain.update_layout(
            xaxis=dict(title="% of Total Investor Population Contacted", range=[0, 100], showgrid=True),
            yaxis=dict(title="% of Total Dormant Investors Captured", range=[0, 100], showgrid=True),
            margin=dict(l=65, r=20, t=15, b=25),
            height=290,
            showlegend=True,
            legend=dict(x=0.03, y=0.97, bgcolor="rgba(0,0,0,0)"),
        )
        apply_chart_theme(fig_gain, height=290)
        st.plotly_chart(fig_gain, width="stretch", config={"displayModeBar": False})

    st.html("<div style='height: 16px;'></div>")

    # 4. Capacity-Constrained Economic Contact Threshold Optimizer
    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Capacity-constrained threshold optimizer</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:12px;">Authoritative segment-level break-even economics constrained by operational CRM outreach capacity</div>'
    )

    # Segment Economics Reference Table
    playbooks = get_segment_playbook()
    be_table_data = []
    for seg_name, pbook in playbooks.items():
        be_r = break_even_risk(seg_name)
        be_table_data.append({
            "Segment": seg_name,
            "Save Rate": f"{pbook.save_rate * 100:.0f}%",
            "Investor LTV": f"₹{pbook.lifetime_value:,.0f}",
            "Unit Contact Cost": f"₹{CONTACT_COST_INR:.0f}",
            "Break-Even Risk (R*)": f"{be_r * 100:.1f}%",
            "Formula Definition": f"₹{CONTACT_COST_INR:.0f} / ({pbook.save_rate:.2f} × ₹{pbook.lifetime_value:,.0f})",
        })
    be_df = pd.DataFrame(be_table_data)

    st.dataframe(
        be_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Segment": st.column_config.TextColumn("Segment", width="small"),
            "Save Rate": st.column_config.TextColumn("Assumed Save Rate", width="small"),
            "Investor LTV": st.column_config.TextColumn("Investor LTV", width="small"),
            "Unit Contact Cost": st.column_config.TextColumn("Contact Cost", width="small"),
            "Break-Even Risk (R*)": st.column_config.TextColumn("Break-Even Risk (R*)", width="small"),
            "Formula Definition": st.column_config.TextColumn("Break-Even Formula (Cost / [Save Rate × LTV])", width="large"),
        },
    )

    st.html("<div style='height: 8px;'></div>")

    # Weekly Capacity Slider
    cap_col1, cap_col2 = st.columns([1.5, 1.0], gap="large")
    with cap_col1:
        capacity_val = st.slider(
            "Weekly CRM outreach capacity (accounts)",
            min_value=500,
            max_value=20000,
            value=5000,
            step=250,
            format="%d accounts/week",
            help="Maximum accounts your CRM or call center operations can contact in this batch",
        )

    # Sort users by Net Expected Value descending
    df_sorted = scores_df.sort_values(by="expected_value", ascending=False).reset_index(drop=True)
    n_breakeven = int((df_sorted["expected_value"] > 0).sum())

    # Recommended contact volume = min(breakeven, capacity)
    rec_contacts = min(n_breakeven, capacity_val)
    is_capacity_binding = capacity_val < n_breakeven

    # Slice contacted cohort
    contacted_cohort = df_sorted.iloc[:rec_contacts]
    portfolio_net_ev = contacted_cohort["expected_value"].sum()
    marginal_ev = df_sorted.iloc[rec_contacts - 1]["expected_value"] if rec_contacts > 0 else 0.0
    marginal_risk = df_sorted.iloc[rec_contacts - 1]["predicted_risk"] if rec_contacts > 0 else 0.0

    with cap_col2:
        status_label = "Capacity-Constrained" if is_capacity_binding else "Economic Break-Even"
        status_tone = "warning" if is_capacity_binding else "positive"
        st.html(
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:10px 14px; margin-top:20px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
            f'<span style="font-size:11px; font-weight:600; color:{t.text_muted}; letter-spacing:0.5px;">OPERATIONAL REGIME</span>'
            f'{render_tag(status_label, status_tone)}'
            f'</div>'
            f'<div style="font-size:12px; color:{t.text_primary};">'
            f'Recommended Cut: <strong style="font-family:IBM Plex Mono;">{rec_contacts:,} accounts</strong> ({rec_contacts / len(scores_df) * 100:.1f}% cohort)<br>'
            f'Marginal Account Net EV: <strong style="font-family:IBM Plex Mono; color:{t.positive};">{format_rupees(marginal_ev)}</strong>'
            f'</div>'
            f'</div>'
        )

    # Optimizer Summary Metric Strip
    opt_metrics = [
        {"label": "Recommended contacts", "value": f"{rec_contacts:,}", "sub": f"min(Break-Even: {n_breakeven:,}, Cap: {capacity_val:,})", "delta": f"{rec_contacts / len(scores_df) * 100:.1f}% of cohort", "delta_good": True},
        {"label": "Portfolio Net Expected Value", "value": format_rupees(portfolio_net_ev, compact=True), "sub": f"Cumulative net return after ₹{CONTACT_COST_INR:.0f} cost", "delta": None},
        {"label": "Marginal EV of last contact", "value": format_rupees(marginal_ev), "sub": f"Account #{rec_contacts:,} (Risk {marginal_risk*100:.1f}%)", "delta": "Positive EV" if marginal_ev > 0 else "Negative EV", "delta_good": marginal_ev > 0},
        {"label": "Break-even reservoir", "value": f"{n_breakeven:,}", "sub": f"{n_breakeven - rec_contacts:,} positive-EV accounts held back", "delta": None},
    ]
    render_metric_strip(opt_metrics)

    # Cumulative Net EV Curve vs Contact Volume Chart
    fig_opt = go.Figure()

    # Pre-calculate curve sampled across 60 points
    curve_steps = np.linspace(500, len(scores_df), 60).astype(int)
    ev_curve = []
    for s in curve_steps:
        ev_curve.append(df_sorted.iloc[:s]["expected_value"].sum())

    fig_opt.add_trace(
        go.Scatter(
            x=curve_steps,
            y=ev_curve,
            mode="lines",
            line=dict(color=t.accent, width=2.5),
            name="Cumulative Net Portfolio EV (₹)",
            hovertemplate="Contacts: %{x:,}<br>Cumulative EV: ₹%{y:,.0f}<extra></extra>",
        )
    )

    # Break-even line
    fig_opt.add_vline(
        x=n_breakeven,
        line=dict(color=t.border, dash="dash", width=1.5),
        annotation_text=f"Break-Even Boundary ({n_breakeven:,} accounts)",
        annotation_position="top left",
        annotation_font=dict(size=10, color=t.text_muted),
    )

    # Operational Cutoff marker
    fig_opt.add_trace(
        go.Scatter(
            x=[rec_contacts],
            y=[portfolio_net_ev],
            mode="markers+text",
            marker=dict(color=t.positive if not is_capacity_binding else t.warning, size=10, symbol="diamond"),
            text=[f" Recommended ({rec_contacts:,}, {format_rupees(portfolio_net_ev, compact=True)})"],
            textposition="top left",
            textfont=dict(size=11, color=t.text_primary, family="IBM Plex Mono"),
            name="Operational Cutoff",
        )
    )

    fig_opt.update_layout(
        xaxis=dict(title="Number of High-EV Accounts Contacted", showgrid=True),
        yaxis=dict(title="Cumulative Net Portfolio EV (₹)", showgrid=True),
        margin=dict(l=65, r=20, t=15, b=25),
        height=280,
        showlegend=False,
    )
    apply_chart_theme(fig_opt, height=280)
    st.plotly_chart(fig_opt, width="stretch", config={"displayModeBar": False})

    # Strategy callout
    if is_capacity_binding:
        rec_msg = (
            f"Capacity-Constrained Policy: At weekly CRM quota of {capacity_val:,} contacts, the optimal strategy reaches the top {rec_contacts:,} accounts ranked by net expected return. "
            f"The marginal contacted account (# {rec_contacts:,}) delivers an incremental net return of {format_rupees(marginal_ev)}. "
            f"An additional {n_breakeven - rec_contacts:,} positive-EV accounts remain uncontacted due to capacity constraints, representing {format_rupees(df_sorted.iloc[:n_breakeven]['expected_value'].sum() - portfolio_net_ev, compact=True)} in unrealized net return."
        )
        render_callout(rec_msg, tone="warning")
    else:
        rec_msg = (
            f"Full Economic Break-Even Policy: Capacity ({capacity_val:,}) exceeds break-even volume ({n_breakeven:,}). Intervene with all {n_breakeven:,} accounts meeting individual segment break-even thresholds R*. "
            f"The final contacted account delivers marginal return of {format_rupees(marginal_ev)}. Contacting beyond {n_breakeven:,} accounts is value-destructive because contact cost (₹{CONTACT_COST_INR:.0f}) exceeds expected gross save value."
        )
        render_callout(rec_msg, tone="neutral")
