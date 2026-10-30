"""Experiment planner view: Sample-size calculator, decision protocol, and A/B result read-out."""

import streamlit as st

from app.ui import (
    COLOR_BORDER,
    COLOR_MUTED_INK,
    COLOR_PETROL,
    COLOR_SURFACE,
    render_callout,
    render_metric_strip,
    render_section_header,
)
from src.stats import calculate_sample_size, two_proportion_z_test


def render() -> None:
    render_section_header(
        "Experiment planner",
        "Statistical sample-size calculator, decision rules, and two-proportion experiment read-out.",
    )

    # 1. Sample Size Calculator
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>1. Sample-size calculator</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 16px;'>Determine the statistical power and sample size required to validate an intervention before rollout.</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        base_rate_pct = st.slider("Baseline save rate (%)", min_value=5.0, max_value=40.0, value=18.0, step=1.0)
    with c2:
        mde_pct = st.slider("Target relative lift / MDE (%)", min_value=5.0, max_value=50.0, value=15.0, step=1.0)
    with c3:
        power_choice = st.selectbox("Statistical power", [0.80, 0.90], index=0, format_func=lambda x: f"{int(x * 100)}% power")
    with c4:
        daily_vol = st.number_input("Daily eligible users", min_value=10, max_value=5000, value=120, step=10)

    # Calculation
    sizing = calculate_sample_size(
        baseline_rate=base_rate_pct / 100.0,
        mde_relative=mde_pct / 100.0,
        alpha=0.05,
        power=power_choice,
        daily_traffic=daily_vol,
    )

    size_metrics = [
        {"label": "Per-variant sample", "value": f"{sizing['sample_size_per_variant']:,}", "sub": "Required per arm"},
        {"label": "Total test cohort", "value": f"{sizing['total_sample_size']:,}", "sub": "Control + Variant"},
        {"label": "Target save rate", "value": f"{sizing['target_rate'] * 100:.2f}%", "sub": f"+{sizing['relative_mde_pct']:.1f}% relative lift"},
        {"label": "Estimated test duration", "value": f"{sizing['estimated_days']} days", "sub": f"At {daily_vol:,} users / day"},
    ]
    render_metric_strip(size_metrics)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Decision Rule Protocol
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>2. Decision rule protocol</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 14px;'>Pre-commit to stopping rules and rollout criteria before deploying traffic.</p>", unsafe_allow_html=True)

    rule_col1, rule_col2, rule_col3 = st.columns(3, gap="medium")
    with rule_col1:
        st.markdown(
            f"""
            <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 14px; height: 100%;">
                <div style="font-weight: 600; font-size: 13px; color: #0E5A6B; margin-bottom: 6px;">Ship to 100% (Rollout)</div>
                <div style="font-size: 12px; color: {COLOR_MUTED_INK}; line-height: 1.5;">
                    - P-value < 0.05 with positive lift.<br>
                    - Confidence interval lower bound > 0.<br>
                    - Net expected return exceeds ₹15 contact cost.<br>
                    - Operational SLA maintained across outreach channels.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rule_col2:
        st.markdown(
            f"""
            <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 14px; height: 100%;">
                <div style="font-weight: 600; font-size: 13px; color: #B7791F; margin-bottom: 6px;">Iterate Variant (Modify)</div>
                <div style="font-size: 12px; color: {COLOR_MUTED_INK}; line-height: 1.5;">
                    - 0.05 <= P-value < 0.20 with directionally positive lift.<br>
                    - Qualitative feedback indicates user message relevance.<br>
                    - Re-evaluate messaging copy, timing, or delivery channel before re-running.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rule_col3:
        st.markdown(
            f"""
            <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 14px; height: 100%;">
                <div style="font-weight: 600; font-size: 13px; color: #A63D40; margin-bottom: 6px;">Abandon (Rollback)</div>
                <div style="font-size: 12px; color: {COLOR_MUTED_INK}; line-height: 1.5;">
                    - P-value >= 0.20 or negative lift.<br>
                    - Net expected return after contact cost <= 0.<br>
                    - Unsubscribe or complaint rate exceeds 1.5%.<br>
                    - Halt intervention and archive test.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 3. Two-Proportion Test Read-Out
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>3. Experiment result read-out</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 16px;'>Evaluate trial results with a two-sample two-sided hypothesis test.</p>", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        ctrl_successes = st.number_input("Control successes (saved)", min_value=0, max_value=100000, value=360, step=10)
    with t2:
        ctrl_n = st.number_input("Control total sample", min_value=1, max_value=200000, value=2000, step=50)
    with t3:
        var_successes = st.number_input("Variant successes (saved)", min_value=0, max_value=100000, value=440, step=10)
    with t4:
        var_n = st.number_input("Variant total sample", min_value=1, max_value=200000, value=2000, step=50)

    try:
        test_res = two_proportion_z_test(
            control_successes=ctrl_successes,
            control_total=ctrl_n,
            variant_successes=var_successes,
            variant_total=var_n,
            alpha=0.05,
        )

        readout_metrics = [
            {"label": "Control save rate", "value": f"{test_res['control_rate'] * 100:.2f}%", "sub": f"{ctrl_successes:,} / {ctrl_n:,}"},
            {"label": "Variant save rate", "value": f"{test_res['variant_rate'] * 100:.2f}%", "sub": f"{var_successes:,} / {var_n:,}"},
            {"label": "Relative lift", "value": f"{test_res['relative_change_pct']:+.2f}%", "sub": f"{test_res['absolute_difference'] * 100:+.2f} pts abs"},
            {"label": "P-value", "value": f"{test_res['p_value']:.4f}", "sub": f"z = {test_res['z_statistic']:.2f}"},
        ]
        render_metric_strip(readout_metrics)

        # Verdict Callout
        if test_res["is_significant"]:
            if test_res["absolute_difference"] > 0:
                render_callout(
                    f"Statistically significant lift: Variant demonstrated a +{test_res['relative_change_pct']:.1f}% relative improvement (p = {test_res['p_value']:.4f}). 95% Confidence Interval for difference: [{test_res['ci_lower'] * 100:.2f}%, {test_res['ci_upper'] * 100:.2f}%]. Meets rollout criteria.",
                    tone="neutral",
                )
            else:
                render_callout(
                    f"Statistically significant drop: Variant performed worse than control by {test_res['relative_change_pct']:.1f}% (p = {test_res['p_value']:.4f}). Rollback immediately.",
                    tone="danger",
                )
        else:
            render_callout(
                f"Inconclusive result: Observed difference is not statistically significant at alpha = 0.05 (p = {test_res['p_value']:.4f}). The 95% Confidence Interval [{test_res['ci_lower'] * 100:.2f}%, {test_res['ci_upper'] * 100:.2f}%] spans zero. Continue test or iterate design.",
                tone="warning",
            )
    except Exception as e:
        st.error(f"Error calculating test: {e}")
