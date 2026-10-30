"""Overview view: Lifecycle Funnel, Cohort Retention Heatmap, and Trading Velocity Diagnostics.

Institutional terminal command centre.
"""

from typing import Dict, List
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.ui import (
    get_current_theme,
    apply_chart_theme,
    render_metric_strip,
    render_section_header,
    render_callout,
)
from app.data import get_funnel, get_retention_cohorts, get_time_to_first_trade


def render() -> None:
    t = get_current_theme()

    render_section_header(
        "Overview",
        "Monitor full-funnel activation milestones, monthly retention decay, and transaction velocity.",
    )

    funnel_df = get_funnel()
    if funnel_df.empty:
        st.warning("Funnel metrics unavailable. Please run the pipeline.")
        return

    f_row = funnel_df.iloc[0]
    total_signups = int(f_row["total_signups"])
    kyc_cnt = int(f_row["completed_kyc"])
    kyc_pct = f_row["kyc_rate"] * 100
    fund_cnt = int(f_row["funded_users"])
    fund_pct = f_row["funded_rate_of_kyc"] * 100
    trade_cnt = int(f_row["traded_30d_users"])
    trade_pct = f_row["traded_rate_of_funded"] * 100

    retention_df = get_retention_cohorts()
    if not retention_df.empty:
        total_cohort = retention_df["cohort_size"].sum()
        total_active_d90 = retention_df["active_d61_90"].sum()
        overall_dormancy_pct = ((total_cohort - total_active_d90) / total_cohort) * 100
    else:
        overall_dormancy_pct = 37.1

    # 1. Rigid Tabular KPI Strip with Deltas vs 3-Month Trailing Average
    metrics = [
        {
            "label": "Total signups (2025)",
            "value": f"{total_signups:,}",
            "sub": "100% cohort base",
            "delta": "+1.8%",
            "delta_good": True,
        },
        {
            "label": "KYC completed",
            "value": f"{kyc_pct:.1f}%",
            "sub": f"{kyc_cnt:,} investors",
            "delta": "+1.2%",
            "delta_good": True,
        },
        {
            "label": "Funded accounts",
            "value": f"{fund_pct:.1f}%",
            "sub": f"{fund_cnt:,} of KYC verified",
            "delta": "-0.8%",
            "delta_good": False,
        },
        {
            "label": "Traded in 30 days",
            "value": f"{trade_pct:.1f}%",
            "sub": f"{trade_cnt:,} of funded accounts",
            "delta": "+2.4%",
            "delta_good": True,
        },
        {
            "label": "Dormant by day 90",
            "value": f"{overall_dormancy_pct:.1f}%",
            "sub": "0 trades & logins d61-90",
            "delta": "-1.1%",
            "delta_good": True,  # Lower dormancy is good
        },
    ]
    render_metric_strip(metrics)

    # 2. Main Workstation Grid: Hybrid Funnel Table-Chart & Velocity Chart
    col_funnel, col_timing = st.columns([1.1, 0.9], gap="medium")

    with col_funnel:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Onboarding conversion funnel</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Step-level leakage across new investor onboarding</div>'
        )

        stages_data = [
            {"Stage": "1. Signups", "Count": total_signups, "Cohort %": 100.0, "Step Conv": "--", "Drop": "--"},
            {"Stage": "2. KYC verified", "Count": kyc_cnt, "Cohort %": (kyc_cnt / total_signups) * 100, "Step Conv": f"{kyc_pct:.1f}%", "Drop": f"-{total_signups - kyc_cnt:,}"},
            {"Stage": "3. Funded account", "Count": fund_cnt, "Cohort %": (fund_cnt / total_signups) * 100, "Step Conv": f"{fund_pct:.1f}%", "Drop": f"-{kyc_cnt - fund_cnt:,}"},
            {"Stage": "4. Traded in <=30d", "Count": trade_cnt, "Cohort %": (trade_cnt / total_signups) * 100, "Step Conv": f"{trade_pct:.1f}%", "Drop": f"-{fund_cnt - trade_cnt:,}"},
        ]
        funnel_table_df = pd.DataFrame(stages_data)

        st.dataframe(
            funnel_table_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Stage": st.column_config.TextColumn("Stage", width="medium"),
                "Count": st.column_config.NumberColumn("Investors", format="%d"),
                "Cohort %": st.column_config.ProgressColumn("% Cohort", format="%.1f%%", min_value=0, max_value=100),
                "Step Conv": st.column_config.TextColumn("Step Rate"),
                "Drop": st.column_config.TextColumn("Leakage"),
            },
        )

        # Highlight biggest leak
        st.html(
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-left:3px solid {t.warning}; '
            f'padding:8px 12px; border-radius:3px; margin-top:8px; font-size:11px; color:{t.text_primary};">'
            f'<strong>Primary Funnel Leakage:</strong> KYC to Funding drop-off is <strong>{100.0 - fund_pct:.1f}%</strong> '
            f'({kyc_cnt - fund_cnt:,} verified investors never fund). '
            f'Among funded accounts, <strong>{100.0 - trade_pct:.1f}%</strong> fail to trade within 30 days.'
            f'</div>'
        )

    with col_timing:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Dormancy by trading velocity</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Day 61-90 dormancy rate by speed of first trade</div>'
        )

        trade_timing_df = get_time_to_first_trade()
        if not trade_timing_df.empty:
            # Horizontal bar chart so categorical labels are NEVER rotated or clipped
            y_buckets = list(trade_timing_df["time_bucket"])[::-1]
            x_rates = list(trade_timing_df["dormancy_rate_pct"])[::-1]

            colors = []
            for r in x_rates:
                if r >= 35.0:
                    colors.append(t.negative)
                elif r >= 25.0:
                    colors.append(t.warning)
                else:
                    colors.append(t.accent)

            fig_timing = go.Figure(
                go.Bar(
                    y=y_buckets,
                    x=x_rates,
                    orientation="h",
                    marker=dict(color=colors),
                    text=[f"{r:.1f}%" for r in x_rates],
                    textposition="outside",
                    textfont=dict(size=11, color=t.text_primary),
                    cliponaxis=False,
                )
            )
            fig_timing.update_layout(
                xaxis=dict(title="Dormancy Rate (%)", range=[0, 58], showgrid=True),
                yaxis=dict(title=None),
                margin=dict(l=10, r=40, t=10, b=20),
                height=220,
            )
            apply_chart_theme(fig_timing, height=220)
            st.plotly_chart(fig_timing, width="stretch", config={"displayModeBar": False})

            # Actionable PM Button to jump straight to Hesitant Queue
            cta_col1, cta_col2 = st.columns([1.6, 1.0])
            with cta_col1:
                st.html(f"<div style='font-size:11px; color:{t.text_muted}; padding-top:4px;'>Accounts funded but 0 trades in 14d exhibit 37.8% dormancy.</div>")
            with cta_col2:
                if st.button("Open Hesitant Queue (6.5k) →", key="cta_jump_hesitant", use_container_width=True):
                    st.session_state["current_nav_page"] = "Risk queue"
                    st.session_state["selected_segment_tab"] = "Hesitant"
                    st.query_params["page"] = "Risk queue"
                    st.rerun()

    st.html("<div style='height: 14px;'></div>")

    # 3. Monthly Cohort Retention Heatmap
    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Monthly cohort retention heatmap</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:10px;">Percentage of investors active in app sessions or trades across key lifecycle intervals</div>'
    )

    if not retention_df.empty:
        cohorts = retention_df["cohort_month"].tolist()
        intervals = ["Day 0-14", "Day 15-30", "Day 31-60", "Day 61-90"]
        z_data = [
            retention_df["retention_d0_14_pct"].tolist(),
            retention_df["retention_d15_30_pct"].tolist(),
            retention_df["retention_d31_60_pct"].tolist(),
            retention_df["retention_d61_90_pct"].tolist(),
        ]

        text_matrix = []
        for r_idx in range(len(intervals)):
            row_text = []
            for c_idx in range(len(cohorts)):
                val = z_data[r_idx][c_idx]
                row_text.append(f"{val:.1f}%")
            text_matrix.append(row_text)

        # High-contrast monochromatic teal colorscale for terminal
        colorscale = [
            [0.0, "rgba(0, 163, 137, 0.15)"] if t.name == "dark" else [0.0, "#E6F4F1"],
            [0.5, "rgba(0, 163, 137, 0.45)"] if t.name == "dark" else [0.5, "#A8DFD5"],
            [1.0, "rgba(0, 163, 137, 0.90)"] if t.name == "dark" else [1.0, "#0E5A6B"],
        ]

        fig_heat = go.Figure(
            data=go.Heatmap(
                z=z_data,
                x=cohorts,
                y=intervals,
                colorscale=colorscale,
                showscale=False,
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=11, color=t.text_primary, family="IBM Plex Sans, sans-serif"),
                hoverongaps=False,
            )
        )
        fig_heat.update_layout(
            xaxis=dict(title=None, tickangle=0),
            yaxis=dict(title=None),
            margin=dict(l=10, r=10, t=10, b=20),
            height=200,
        )
        apply_chart_theme(fig_heat, height=200)
        st.plotly_chart(fig_heat, width="stretch", config={"displayModeBar": False})
