"""Segments and playbook view: Expected value by segment, summary table, and detailed playbook per segment."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.ui import (
    COLOR_BORDER,
    COLOR_GRIDLINE,
    COLOR_INK,
    COLOR_MUTED_INK,
    COLOR_PETROL,
    COLOR_SURFACE,
    apply_chart_theme,
    format_rupees,
    render_callout,
    render_metric_strip,
    render_section_header,
)
from app.data import get_scores
from src.config import CONTACT_COST_INR, SEGMENT_PLAYBOOK
from src.segments import compute_segment_summary


SEGMENT_DESCRIPTIONS = {
    "Burned": "Traded and worst trade P&L <= -₹250 in days 0-14.",
    "Hesitant": "Account funded, but zero trades placed in days 0-14.",
    "Browser": "Account unfunded, but added 6+ stocks to watchlist in days 0-14.",
    "Unfunded": "Account unfunded (< 6 watchlist adds in days 0-14).",
    "Monitor": "Active, funded investors with regular activity or profitable trades.",
}


def render() -> None:
    render_section_header(
        "Segments and playbook",
        "Deterministic behavioral segment economics, expected net returns, and intervention playbook.",
    )

    scores_df = get_scores()
    if scores_df.empty:
        st.warning("User scores unavailable. Please run the pipeline.")
        return

    summary_df = compute_segment_summary(scores_df)

    # 1. Ruled Metric Strip
    tot_users = len(scores_df)
    tot_contactable = int(scores_df["should_contact"].sum())
    tot_ev = scores_df["expected_value"].sum()
    avg_ev_contact = scores_df[scores_df["should_contact"]]["expected_value"].mean()

    metrics = [
        {"label": "Total cohort", "value": f"{tot_users:,}", "sub": "5 behavioral segments"},
        {"label": "Contactable users", "value": f"{tot_contactable:,}", "sub": "Positive net expected value"},
        {"label": "Total net expected return", "value": format_rupees(tot_ev, compact=True), "sub": f"After ₹{CONTACT_COST_INR:.0f} contact cost"},
        {"label": "Average EV per contacted user", "value": format_rupees(avg_ev_contact), "sub": "Net incremental value"},
    ]
    render_metric_strip(metrics)

    # 2. Expected Value by Segment Chart & Summary Table (2-column layout)
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Net expected value by segment</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Total incremental value generated across each segment after contact costs</p>", unsafe_allow_html=True)

        chart_df = summary_df.sort_values(by="total_expected_value", ascending=True)

        fig_ev = go.Figure(
            go.Bar(
                y=chart_df["segment"],
                x=chart_df["total_expected_value"],
                orientation="h",
                marker=dict(color=COLOR_PETROL),
                text=[format_rupees(v, compact=True) for v in chart_df["total_expected_value"]],
                textposition="outside",
                textfont=dict(size=11, color=COLOR_INK),
            )
        )
        fig_ev.update_layout(
            xaxis=dict(title="Net Expected Value (₹)", showgrid=True),
            yaxis=dict(title=None),
            margin=dict(l=10, r=40, t=10, b=20),
            height=280,
        )
        apply_chart_theme(fig_ev, height=280)
        st.plotly_chart(fig_ev, use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Segment distribution</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>User count and average predicted dormancy risk per segment</p>", unsafe_allow_html=True)

        fig_dist = go.Figure(
            go.Bar(
                x=summary_df["segment"],
                y=summary_df["user_count"],
                marker=dict(color="#5B97A4"),
                text=[f"{cnt:,} ({pct}%)" for cnt, pct in zip(summary_df["user_count"], summary_df["user_pct"])],
                textposition="outside",
                textfont=dict(size=11, color=COLOR_INK),
            )
        )
        fig_dist.update_layout(
            xaxis=dict(title=None),
            yaxis=dict(title="Users", showgrid=True),
            margin=dict(l=10, r=10, t=10, b=20),
            height=280,
        )
        apply_chart_theme(fig_dist, height=280)
        st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Summary Table
    st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Segment economics summary table</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Assumed unit economics, contactable volume, and expected value parameters</p>", unsafe_allow_html=True)

    tbl_df = summary_df.copy()
    tbl_display = pd.DataFrame({
        "Segment": tbl_df["segment"],
        "Users": tbl_df["user_count"].apply(lambda u: f"{u:,}"),
        "Share (%)": tbl_df["user_pct"].apply(lambda p: f"{p:.1f}%"),
        "Avg risk": tbl_df["avg_risk"].apply(lambda r: f"{r * 100:.1f}%"),
        "Save rate": tbl_df["save_rate"].apply(lambda s: f"{s * 100:.0f}%"),
        "LTV (₹)": tbl_df["lifetime_value"].apply(lambda l: format_rupees(l)),
        "Net EV (₹)": tbl_df["total_expected_value"].apply(lambda e: format_rupees(e)),
        "Contactable": tbl_df["contactable_users"].apply(lambda c: f"{c:,}"),
        "Primary channel": tbl_df["channel"],
    })

    st.dataframe(tbl_display, use_container_width=True, hide_index=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 4. Playbook per Segment Cards
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>Playbook per segment</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 16px;'>Standard operating intervention procedures and message copy declared in configuration.</p>", unsafe_allow_html=True)

    for seg_name, pbook in SEGMENT_PLAYBOOK.items():
        rule_desc = SEGMENT_DESCRIPTIONS.get(seg_name, "")
        seg_stats = summary_df[summary_df["segment"] == seg_name].iloc[0]

        st.markdown(
            f"""
            <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 18px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                    <div style="font-weight: 700; font-size: 15px; color: {COLOR_INK};">{seg_name}</div>
                    <div style="font-size: 12px; color: {COLOR_MUTED_INK};">Rule: <em>{rule_desc}</em></div>
                </div>
                <div style="font-size: 12px; color: {COLOR_MUTED_INK}; margin-bottom: 12px; border-bottom: 1px solid {COLOR_BORDER}; padding-bottom: 8px;">
                    Users: <strong>{seg_stats['user_count']:,}</strong> ({seg_stats['user_pct']}%) &nbsp;|&nbsp;
                    Avg risk: <strong>{seg_stats['avg_risk'] * 100:.1f}%</strong> &nbsp;|&nbsp;
                    Assumed save rate: <strong>{pbook.save_rate * 100:.0f}%</strong> &nbsp;|&nbsp;
                    LTV: <strong>{format_rupees(pbook.lifetime_value)}</strong> &nbsp;|&nbsp;
                    Net EV: <strong>{format_rupees(seg_stats['total_expected_value'])}</strong>
                </div>
                <div style="font-size: 13px; margin-bottom: 4px;"><strong>Recommended action:</strong> {pbook.action}</div>
                <div style="font-size: 13px; margin-bottom: 10px;"><strong>Channel:</strong> {pbook.channel} &nbsp;|&nbsp; <strong>Contact decision:</strong> Contact if (Risk x {pbook.save_rate} x ₹{pbook.lifetime_value:,.0f}) > ₹{CONTACT_COST_INR:.0f}</div>
                <div style="font-size: 12px; font-weight: 600; color: {COLOR_MUTED_INK}; margin-bottom: 4px;">Standard copy template:</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_callout(f'"{pbook.message}"', tone="neutral")
