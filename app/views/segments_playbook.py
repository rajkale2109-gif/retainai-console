"""Segments and playbook view: Deterministic behavioral segment economics, ledger table, and integrated playbook tabs."""

from typing import Dict
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.ui import (
    get_current_theme,
    apply_chart_theme,
    format_rupees,
    render_metric_strip,
    render_section_header,
    render_tag,
)
from app.data import get_scores
from src.config import CONTACT_COST_INR
from src.economics import get_segment_playbook, break_even_risk
from src.segments import compute_segment_summary


SEGMENT_RULES = {
    "Hesitant": "Account funded with capital, but zero delivery or intraday trades placed within first 14 days.",
    "Burned": "Placed at least 1 trade and incurred an early realized loss (worst trade P&L <= -₹250).",
    "Browser": "Account remains unfunded, but demonstrated high engagement with 6+ stocks added to watchlist.",
    "Unfunded": "Account remains unfunded with passive or low watchlist activity (< 6 watchlist adds).",
    "Monitor": "Active, funded investors with regular trading cadence or profitable trade outcomes.",
}


def render() -> None:
    t = get_current_theme()

    render_section_header(
        "Segments and playbook",
        "Deterministic behavioral segment economics, expected net returns, and intervention playbook.",
    )

    scores_df = get_scores()
    if scores_df.empty:
        st.warning("User scores unavailable. Please run the pipeline.")
        return

    summary_df = compute_segment_summary(scores_df)

    # 1. Authoritative Ruled Metric Strip
    tot_users = len(scores_df)
    tot_contactable = int(scores_df["should_contact"].sum())
    tot_ev = scores_df["expected_value"].sum()
    avg_ev_contact = scores_df[scores_df["should_contact"]]["expected_value"].mean()

    metrics = [
        {"label": "Total cohort", "value": f"{tot_users:,}", "sub": "5 behavioral segments", "delta": None},
        {"label": "Contactable accounts", "value": f"{tot_contactable:,}", "sub": "Positive net expected value", "delta": "+90.8% of base", "delta_good": True},
        {"label": "Total net expected return", "value": format_rupees(tot_ev, compact=True), "sub": f"After ₹{CONTACT_COST_INR:.0f} unit contact cost", "delta": None},
        {"label": "Average EV per contact", "value": format_rupees(avg_ev_contact), "sub": "Net incremental value / outreach", "delta": None},
    ]
    render_metric_strip(metrics)

    # 2. Main Ledger & Visual Net EV Distribution
    col_chart, col_ledger = st.columns([0.85, 1.15], gap="medium")

    with col_chart:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Net expected value by segment</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Total incremental return after ₹15 contact cost</div>'
        )

        chart_df = summary_df.sort_values(by="total_expected_value", ascending=True)

        max_val = max(0.0, float(chart_df["total_expected_value"].max())) * 1.25
        min_val = min(0.0, float(chart_df["total_expected_value"].min())) * 3.5

        fig_ev = go.Figure(
            go.Bar(
                y=chart_df["segment"],
                x=chart_df["total_expected_value"],
                orientation="h",
                marker=dict(color=t.accent),
                text=[format_rupees(v, compact=True) for v in chart_df["total_expected_value"]],
                textposition=["inside" if v < 0 else "outside" for v in chart_df["total_expected_value"]],
                textfont=dict(size=11, color=t.text_primary, family="IBM Plex Mono"),
                cliponaxis=False,
            )
        )
        fig_ev.update_layout(
            xaxis=dict(title="Net Expected Value (₹)", showgrid=True, range=[min_val, max_val]),
            yaxis=dict(title=None, tickfont=dict(size=11, color=t.text_primary)),
            margin=dict(l=65, r=50, t=10, b=25),
            height=240,
        )
        apply_chart_theme(fig_ev, height=240)
        st.plotly_chart(fig_ev, width="stretch", config={"displayModeBar": False})

    with col_ledger:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Segment economics ledger</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Unit economics parameters, break-even risk, and contactable volume</div>'
        )

        tbl_data = []
        for _, row in summary_df.iterrows():
            seg_name = row["segment"]
            be_risk = break_even_risk(seg_name)
            tbl_data.append({
                "Segment": seg_name,
                "Accounts": int(row["user_count"]),
                "Share": float(row["user_pct"]),
                "Avg Risk": float(row["avg_risk"] * 100),
                "Save Rate": float(row["save_rate"] * 100),
                "LTV (₹)": float(row["lifetime_value"]),
                "Net EV (₹)": float(row["total_expected_value"]),
                "Break-Even Risk": float(be_risk * 100),
                "Channel": row["channel"],
            })
        ledger_df = pd.DataFrame(tbl_data)

        st.dataframe(
            ledger_df,
            width="stretch",
            hide_index=True,
            height=240,
            column_config={
                "Segment": st.column_config.TextColumn("Segment", width="small"),
                "Accounts": st.column_config.NumberColumn("Accounts", format="%d"),
                "Share": st.column_config.NumberColumn("Share %", format="%.1f%%"),
                "Avg Risk": st.column_config.NumberColumn("Avg Risk", format="%.1f%%"),
                "Save Rate": st.column_config.NumberColumn("Save Rate", format="%.0f%%"),
                "LTV (₹)": st.column_config.NumberColumn("LTV", format="₹%d"),
                "Net EV (₹)": st.column_config.NumberColumn("Net EV", format="₹%d"),
                "Break-Even Risk": st.column_config.NumberColumn("Break-Even R*", format="%.1f%%"),
                "Channel": st.column_config.TextColumn("Channel", width="small"),
            },
        )

    st.html("<div style='height: 16px;'></div>")

    # 3. Playbook per Segment Tabs (Integrated Quote & Template Container - FIX FOR ISSUE e)
    st.html(
        f'<div style="font-weight:600; font-size:14px; color:{t.text_primary}; margin-bottom:2px;">Operational playbook per segment</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:12px;">Standard operating intervention procedures and messaging copy declared in configuration.</div>'
    )

    playbook_dict = get_segment_playbook()
    tab_names = ["Hesitant", "Burned", "Browser", "Unfunded", "Monitor"]
    playbook_tabs = st.tabs(tab_names)

    for idx, seg_name in enumerate(tab_names):
        pbook = playbook_dict[seg_name]
        rule_desc = SEGMENT_RULES.get(seg_name, "")
        seg_stats = summary_df[summary_df["segment"] == seg_name].iloc[0]
        be_risk_pct = break_even_risk(seg_name) * 100.0

        with playbook_tabs[idx]:
            # Integrated container enclosing metadata, trigger rule, and message template together
            card_html = (
                f'<div style="background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:16px; margin-top:8px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px solid {t.border}; padding-bottom:8px; margin-bottom:12px;">'
                f'<div>'
                f'<span style="font-weight:700; font-size:15px; color:{t.text_primary};">{seg_name}</span>'
                f'<span style="margin-left:8px;">{render_tag(pbook.channel, "accent")}</span>'
                f'</div>'
                f'<div style="font-size:11px; color:{t.text_muted};">'
                f'Accounts: <strong>{seg_stats["user_count"]:,}</strong> ({seg_stats["user_pct"]}%) | '
                f'Net EV Contribution: <strong style="color:{t.positive};">{format_rupees(seg_stats["total_expected_value"])}</strong>'
                f'</div>'
                f'</div>'
                f'<div style="font-size:12px; color:{t.text_primary}; margin-bottom:10px;">'
                f'<strong>Trigger Rule:</strong> <em>{rule_desc}</em>'
                f'</div>'
                f'<div style="display:flex; gap:20px; font-size:11px; color:{t.text_muted}; background:{t.raised}; border:1px solid {t.border}; border-radius:3px; padding:8px 12px; margin-bottom:12px;">'
                f'<span>Avg Predicted Risk: <strong style="color:{t.text_primary};">{seg_stats["avg_risk"] * 100:.1f}%</strong></span>'
                f'<span>Assumed Save Rate: <strong style="color:{t.text_primary};">{pbook.save_rate * 100:.0f}%</strong></span>'
                f'<span>Investor LTV: <strong style="color:{t.text_primary};">{format_rupees(pbook.lifetime_value)}</strong></span>'
                f'<span>Break-Even Risk (R*): <strong style="color:{t.warning};">{be_risk_pct:.1f}%</strong></span>'
                f'<span>Contact Rule: <strong>Risk &ge; {be_risk_pct:.1f}%</strong></span>'
                f'</div>'
                f'<div style="font-size:12px; color:{t.text_primary}; margin-bottom:8px;">'
                f'<strong>Standard Action:</strong> {pbook.action}'
                f'</div>'
                f'<div style="font-size:11px; font-weight:600; color:{t.text_muted}; margin-bottom:4px; letter-spacing:0.5px;">STANDARDIZED COPY TEMPLATE:</div>'
                f'<div style="background:{t.canvas}; border:1px solid {t.border}; border-left:3px solid {t.accent}; border-radius:3px; padding:10px 14px; font-size:12px; color:{t.text_primary}; font-style:italic; line-height:1.5;">'
                f'"{pbook.message}"'
                f'</div>'
                f'</div>'
            )
            st.html(card_html)
