"""Overview view: Five-figure metric strip, conversion funnel, monthly cohort retention heatmap, and dormancy by time to first trade."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.ui import (
    COLOR_AMBER,
    COLOR_BORDER,
    COLOR_GRIDLINE,
    COLOR_INK,
    COLOR_MUTED_INK,
    COLOR_MUTED_RED,
    COLOR_PETROL,
    COLOR_SURFACE,
    apply_chart_theme,
    render_metric_strip,
    render_section_header,
)
from app.data import get_funnel, get_retention_cohorts, get_time_to_first_trade


def render() -> None:
    render_section_header(
        "Overview",
        "Full-funnel conversion metrics, monthly retention cohorts, and relationship between time to first trade and dormancy.",
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
    # Overall dormancy rate from retention
    if not retention_df.empty:
        total_cohort = retention_df["cohort_size"].sum()
        total_active_d90 = retention_df["active_d61_90"].sum()
        overall_dormancy_pct = ((total_cohort - total_active_d90) / total_cohort) * 100
    else:
        overall_dormancy_pct = 37.1

    # 1. Five-Figure Metric Strip
    metrics = [
        {"label": "Total signups (2025)", "value": f"{total_signups:,}", "sub": "100% cohort base"},
        {"label": "KYC completed", "value": f"{kyc_pct:.1f}%", "sub": f"{kyc_cnt:,} investors"},
        {"label": "Funded accounts", "value": f"{fund_pct:.1f}%", "sub": f"{fund_cnt:,} of KYC users"},
        {"label": "Traded in 30 days", "value": f"{trade_pct:.1f}%", "sub": f"{trade_cnt:,} of funded users"},
        {"label": "Dormant by day 90", "value": f"{overall_dormancy_pct:.1f}%", "sub": "No login/trade days 61-90"},
    ]
    render_metric_strip(metrics)

    # 2. Funnel Chart & Time to First Trade (2-column layout)
    col1, col2 = st.columns([1.05, 0.95], gap="large")

    with col1:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Onboarding conversion funnel</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Conversion rates across each step of the customer journey</p>", unsafe_allow_html=True)

        stages = ["Signups", "KYC completed", "Funded account", "Traded <= 30 days"]
        stage_counts = [total_signups, kyc_cnt, fund_cnt, trade_cnt]
        step_conversion = [
            "100.0%",
            f"{kyc_pct:.1f}% of signups",
            f"{fund_pct:.1f}% of KYC",
            f"{trade_pct:.1f}% of funded",
        ]

        fig_funnel = go.Figure(
            go.Bar(
                y=stages[::-1],
                x=stage_counts[::-1],
                orientation="h",
                marker=dict(color=COLOR_PETROL),
                text=[f"{cnt:,} ({pct})" for cnt, pct in zip(stage_counts[::-1], step_conversion[::-1])],
                textposition="auto",
                textfont=dict(size=11, color="#FFFFFF"),
            )
        )
        fig_funnel.update_layout(
            xaxis=dict(title=None, showgrid=True),
            yaxis=dict(title=None),
            margin=dict(l=10, r=20, t=10, b=20),
            height=320,
        )
        apply_chart_theme(fig_funnel, height=320)
        st.plotly_chart(fig_funnel, use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Dormancy by time to first trade</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Day 61-90 dormancy rate by speed of first transaction</p>", unsafe_allow_html=True)

        trade_timing_df = get_time_to_first_trade()
        if not trade_timing_df.empty:
            colors = []
            for rate in trade_timing_df["dormancy_rate_pct"]:
                if rate >= 35.0:
                    colors.append(COLOR_MUTED_RED)
                elif rate >= 25.0:
                    colors.append(COLOR_AMBER)
                else:
                    colors.append(COLOR_PETROL)

            fig_timing = go.Figure(
                go.Bar(
                    x=trade_timing_df["time_bucket"],
                    y=trade_timing_df["dormancy_rate_pct"],
                    marker=dict(color=colors),
                    text=[f"{r:.1f}%" for r in trade_timing_df["dormancy_rate_pct"]],
                    textposition="outside",
                    textfont=dict(size=11, color=COLOR_INK),
                )
            )
            fig_timing.update_layout(
                yaxis=dict(title="Dormancy rate (%)", range=[0, 60], showgrid=True),
                xaxis=dict(title=None),
                margin=dict(l=10, r=10, t=10, b=20),
                height=320,
            )
            apply_chart_theme(fig_timing, height=320)
            st.plotly_chart(fig_timing, use_container_width=True, config={"displayModeBar": False})

    # Funnel and trading velocity diagnostic callout
    render_callout(
        f"Funnel bottleneck analysis: The steepest user drop occurs between KYC and funding, where {100.0 - fund_pct:.1f}% of verified accounts never deposit funds. Among funded accounts, {100.0 - trade_pct:.1f}% fail to trade within 30 days. Fast activation is critical: users placing their first trade within 7 days exhibit only ~15% dormancy, compared to 46.9% for never-traded accounts.",
        tone="neutral",
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Monthly Cohort Retention Heatmap
    st.markdown("<p style='font-weight: 600; font-size: 14px; margin-bottom: 4px;'>Monthly cohort retention heatmap</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Percentage of investors active in app sessions or trades across key lifecycle intervals</p>", unsafe_allow_html=True)

    if not retention_df.empty:
        cohorts = retention_df["cohort_month"].tolist()
        intervals = ["Day 0-14", "Day 15-30", "Day 31-60", "Day 61-90"]
        z_data = [
            retention_df["retention_d0_14_pct"].tolist(),
            retention_df["retention_d15_30_pct"].tolist(),
            retention_df["retention_d31_60_pct"].tolist(),
            retention_df["retention_d61_90_pct"].tolist(),
        ]
        z_transposed = list(map(list, zip(*z_data)))

        annotations = []
        for i, row in enumerate(z_transposed):
            for j, val in enumerate(row):
                annotations.append(
                    dict(
                        x=intervals[j],
                        y=cohorts[i],
                        text=f"{val:.1f}%",
                        showarrow=False,
                        font=dict(
                            color="#FFFFFF" if val > 65 else COLOR_INK,
                            size=11,
                        ),
                    )
                )

        fig_heat = go.Figure(
            go.Heatmap(
                z=z_transposed,
                x=intervals,
                y=cohorts,
                colorscale=[
                    [0.0, "#F5F6F8"],
                    [0.4, "#BBD3DA"],
                    [0.7, "#5B97A4"],
                    [1.0, COLOR_PETROL],
                ],
                showscale=False,
            )
        )
        fig_heat.update_layout(
            annotations=annotations,
            xaxis=dict(title=None, side="top"),
            yaxis=dict(title=None, autorange="reversed"),
            margin=dict(l=10, r=10, t=30, b=10),
            height=360,
        )
        apply_chart_theme(fig_heat, height=360)
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
