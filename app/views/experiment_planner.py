"""Experiment planner view: Statistical sample-size calculator, power curves, dynamic decision protocols, and A/B result read-out."""

from typing import Dict, Any
import streamlit as st
import plotly.graph_objects as go
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
from src.config import CONTACT_COST_INR
from src.economics import get_segment_playbook
from src.stats import calculate_sample_size, two_proportion_z_test


def _sync_slider_to_num(slider_key: str, num_key: str) -> None:
    """Callback to synchronize slider changes into number input."""
    st.session_state[num_key] = st.session_state[slider_key]


def _sync_num_to_slider(num_key: str, slider_key: str) -> None:
    """Callback to synchronize number input changes into slider."""
    st.session_state[slider_key] = st.session_state[num_key]


def render() -> None:
    t = get_current_theme()

    render_section_header(
        "Experiment planner",
        "Statistical sample-size power calculator, decision rule protocol, and two-proportion experiment read-out.",
    )

    # 1. Segment Preset Selection via Segmented Control
    playbooks = get_segment_playbook()
    preset_options = ["Hesitant", "Burned", "Browser", "Unfunded", "Monitor", "Custom"]

    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Preload segment assumptions</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:8px;">Select a target segment to populate baseline save rate, customer LTV, and typical volume</div>'
    )

    selected_segment = st.segmented_control(
        "Target Segment",
        preset_options,
        default="Hesitant",
        label_visibility="collapsed",
    )
    if not selected_segment:
        selected_segment = "Hesitant"

    # Default values mapped from segment economics
    segment_defaults = {
        "Hesitant": {"rate": 24.0, "mde": 15.0, "power": 80, "traffic": 120, "ltv": 1800.0},
        "Burned": {"rate": 18.0, "mde": 15.0, "power": 80, "traffic": 90, "ltv": 1200.0},
        "Browser": {"rate": 15.0, "mde": 20.0, "power": 80, "traffic": 150, "ltv": 800.0},
        "Unfunded": {"rate": 8.0, "mde": 25.0, "power": 80, "traffic": 300, "ltv": 500.0},
        "Monitor": {"rate": 4.0, "mde": 30.0, "power": 80, "traffic": 250, "ltv": 2500.0},
        "Custom": {"rate": 18.0, "mde": 15.0, "power": 80, "traffic": 100, "ltv": 1500.0},
    }
    defaults = segment_defaults.get(selected_segment, segment_defaults["Custom"])

    # Initialize session state keys for linked inputs if segment changed or uninitialized
    last_seg_key = "exp_planner_last_segment"
    if st.session_state.get(last_seg_key) != selected_segment:
        st.session_state[last_seg_key] = selected_segment
        st.session_state["exp_base_rate_slider"] = float(defaults["rate"])
        st.session_state["exp_base_rate_num"] = float(defaults["rate"])
        st.session_state["exp_mde_slider"] = float(defaults["mde"])
        st.session_state["exp_mde_num"] = float(defaults["mde"])
        st.session_state["exp_power_slider"] = int(defaults["power"])
        st.session_state["exp_power_num"] = int(defaults["power"])
        st.session_state["exp_traffic_slider"] = int(defaults["traffic"])
        st.session_state["exp_traffic_num"] = int(defaults["traffic"])

    # Linked Inputs Grid: 4 columns, each containing slider with unit suffix + linked number box
    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-top:14px; margin-bottom:4px;">1. Statistical power & sample-size parameters</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:12px;">Visible bounds [min, max] with two-way linked numeric controls and unit suffixes.</div>'
    )

    c1, c2, c3, c4 = st.columns(4, gap="medium")

    with c1:
        st.html(
            f'<div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:{t.text_primary}; margin-bottom:2px;">'
            f'<span>Baseline Save Rate</span>'
            f'<span style="font-family:IBM Plex Mono, monospace; color:{t.text_muted}; font-size:11px;">[1.0% &ndash; 50.0%]</span>'
            f'</div>'
        )
        sub_c1, sub_c2 = st.columns([1.6, 1.0])
        with sub_c1:
            st.slider(
                "Baseline save rate slider",
                min_value=1.0,
                max_value=50.0,
                step=0.5,
                key="exp_base_rate_slider",
                format="%.1f%%",
                label_visibility="collapsed",
                on_change=_sync_slider_to_num,
                args=("exp_base_rate_slider", "exp_base_rate_num"),
            )
        with sub_c2:
            st.number_input(
                "Baseline rate num",
                min_value=1.0,
                max_value=50.0,
                step=0.5,
                key="exp_base_rate_num",
                label_visibility="collapsed",
                on_change=_sync_num_to_slider,
                args=("exp_base_rate_num", "exp_base_rate_slider"),
            )

    with c2:
        st.html(
            f'<div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:{t.text_primary}; margin-bottom:2px;">'
            f'<span>Target Relative Lift (MDE)</span>'
            f'<span style="font-family:IBM Plex Mono, monospace; color:{t.text_muted}; font-size:11px;">[2.0% &ndash; 50.0%]</span>'
            f'</div>'
        )
        sub_c3, sub_c4 = st.columns([1.6, 1.0])
        with sub_c3:
            st.slider(
                "Target relative lift slider",
                min_value=2.0,
                max_value=50.0,
                step=1.0,
                key="exp_mde_slider",
                format="%.1f%%",
                label_visibility="collapsed",
                on_change=_sync_slider_to_num,
                args=("exp_mde_slider", "exp_mde_num"),
            )
        with sub_c4:
            st.number_input(
                "Target relative lift num",
                min_value=2.0,
                max_value=50.0,
                step=1.0,
                key="exp_mde_num",
                label_visibility="collapsed",
                on_change=_sync_num_to_slider,
                args=("exp_mde_num", "exp_mde_slider"),
            )

    with c3:
        st.html(
            f'<div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:{t.text_primary}; margin-bottom:2px;">'
            f'<span>Statistical Power (1 &minus; &beta;)</span>'
            f'<span style="font-family:IBM Plex Mono, monospace; color:{t.text_muted}; font-size:11px;">[70% &ndash; 95%]</span>'
            f'</div>'
        )
        sub_c5, sub_c6 = st.columns([1.6, 1.0])
        with sub_c5:
            st.slider(
                "Statistical power slider",
                min_value=70,
                max_value=95,
                step=5,
                key="exp_power_slider",
                format="%d%%",
                label_visibility="collapsed",
                on_change=_sync_slider_to_num,
                args=("exp_power_slider", "exp_power_num"),
            )
        with sub_c6:
            st.number_input(
                "Statistical power num",
                min_value=70,
                max_value=95,
                step=5,
                key="exp_power_num",
                label_visibility="collapsed",
                on_change=_sync_num_to_slider,
                args=("exp_power_num", "exp_power_slider"),
            )

    with c4:
        st.html(
            f'<div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:{t.text_primary}; margin-bottom:2px;">'
            f'<span>Daily Eligible Volume</span>'
            f'<span style="font-family:IBM Plex Mono, monospace; color:{t.text_muted}; font-size:11px;">[10 &ndash; 2,500/day]</span>'
            f'</div>'
        )
        sub_c7, sub_c8 = st.columns([1.6, 1.0])
        with sub_c7:
            st.slider(
                "Daily volume slider",
                min_value=10,
                max_value=2500,
                step=25,
                key="exp_traffic_slider",
                format="%d/day",
                label_visibility="collapsed",
                on_change=_sync_slider_to_num,
                args=("exp_traffic_slider", "exp_traffic_num"),
            )
        with sub_c8:
            st.number_input(
                "Daily volume num",
                min_value=10,
                max_value=2500,
                step=25,
                key="exp_traffic_num",
                label_visibility="collapsed",
                on_change=_sync_num_to_slider,
                args=("exp_traffic_num", "exp_traffic_slider"),
            )

    # Calculation values
    cur_base_rate = float(st.session_state["exp_base_rate_num"]) / 100.0
    cur_mde_rel = float(st.session_state["exp_mde_num"]) / 100.0
    cur_power = float(st.session_state["exp_power_num"]) / 100.0
    cur_traffic = int(st.session_state["exp_traffic_num"])

    sizing = calculate_sample_size(
        baseline_rate=cur_base_rate,
        mde_relative=cur_mde_rel,
        alpha=0.05,
        power=cur_power,
        daily_traffic=cur_traffic,
    )

    n_per_variant = sizing["sample_size_per_variant"]
    n_total = sizing["total_sample_size"]
    target_rate = sizing["target_rate"]
    test_days = sizing["estimated_days"]

    # Calculate projected incremental net financial gain
    seg_ltv = defaults.get("ltv", 1500.0)
    incremental_saved_users = n_per_variant * (target_rate - cur_base_rate)
    projected_net_gain = (incremental_saved_users * seg_ltv) - (n_per_variant * CONTACT_COST_INR)

    # 2. Results Metric Strip
    size_metrics = [
        {"label": "Per-variant sample", "value": f"{n_per_variant:,}", "sub": f"Required per arm (&alpha;=0.05, &beta;={1.0-cur_power:.2f})", "delta": None},
        {"label": "Total cohort required", "value": f"{n_total:,}", "sub": "50/50 Control vs Variant split", "delta": None},
        {"label": "Target save rate", "value": f"{target_rate * 100:.2f}%", "sub": f"+{cur_mde_rel * 100:.1f}% relative lift over base", "delta": f"+{(target_rate - cur_base_rate)*100:.2f} pts", "delta_good": True},
        {"label": "Estimated test duration", "value": f"{test_days} days", "sub": f"At {cur_traffic:,} eligible accounts/day", "delta": f"{(test_days/7.0):.1f} weeks", "delta_good": None},
        {"label": "Projected Net Gain", "value": format_rupees(projected_net_gain, compact=True), "sub": f"At ₹{seg_ltv:,.0f} LTV & ₹{CONTACT_COST_INR:.0f} cost", "delta": format_rupees(projected_net_gain / n_per_variant) + "/user", "delta_good": projected_net_gain > 0},
    ]
    render_metric_strip(size_metrics)

    # 3. Sample-Size vs Detectable-Lift Power Curve & Operational Parameters (2 Columns)
    col_curve, col_protocol = st.columns([1.1, 0.9], gap="medium")

    with col_curve:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Sample size vs detectable lift curve</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:8px;">Trade-off between minimum detectable relative lift (MDE) and required cohort size per variant</div>'
        )

        mde_axis = np.linspace(0.04, 0.45, 42)
        samples_curve = []
        for m in mde_axis:
            res = calculate_sample_size(
                baseline_rate=cur_base_rate,
                mde_relative=m,
                alpha=0.05,
                power=cur_power,
                daily_traffic=cur_traffic,
            )
            samples_curve.append(res["sample_size_per_variant"])

        fig_curve = go.Figure()
        fig_curve.add_trace(
            go.Scatter(
                x=[m * 100 for m in mde_axis],
                y=samples_curve,
                mode="lines",
                line=dict(color=t.accent, width=2.5),
                name=f"Power {int(cur_power * 100)}% (&alpha;=0.05)",
                hovertemplate="MDE: %{x:.1f}%<br>Sample / arm: %{y:,.0f}<extra></extra>",
            )
        )

        # Operational setting marker
        fig_curve.add_trace(
            go.Scatter(
                x=[cur_mde_rel * 100],
                y=[n_per_variant],
                mode="markers+text",
                marker=dict(color=t.negative, size=9, symbol="circle"),
                text=[f" Current ({cur_mde_rel*100:.1f}%, {n_per_variant:,})"],
                textposition="top right",
                textfont=dict(size=11, color=t.text_primary, family="IBM Plex Mono"),
                name="Configured Setting",
            )
        )

        fig_curve.update_layout(
            xaxis=dict(
                title="Target Relative Lift / MDE (%)",
                showgrid=True,
                zeroline=False,
                dtick=5,
            ),
            yaxis=dict(
                title="Required Sample Size per Arm",
                showgrid=True,
                zeroline=False,
            ),
            margin=dict(l=65, r=20, t=15, b=25),
            height=280,
            showlegend=False,
        )
        apply_chart_theme(fig_curve, height=280)
        st.plotly_chart(fig_curve, width="stretch", config={"displayModeBar": False})

    with col_protocol:
        st.html(
            f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">Pre-commit decision rules</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:8px;">Dynamically calculated thresholds parameterized by current input settings</div>'
        )

        # Ship, Iterate, Stop Cards with dynamically injected values
        st.html(
            f'<div style="display:flex; flex-direction:column; gap:8px;">'
            # Ship card
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-left:3px solid {t.positive}; border-radius:3px; padding:10px 12px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
            f'<span style="font-weight:700; font-size:12px; color:{t.positive}; letter-spacing:0.3px;">SHIP TO 100% (ROLLOUT)</span>'
            f'{render_tag(f"&ge; {target_rate * 100:.2f}% Save Rate", "positive")}'
            f'</div>'
            f'<div style="font-size:11px; color:{t.text_primary}; line-height:1.4;">'
            f'&bull; Two-tailed p-value &lt; <strong>0.050</strong> with directional positive lift.<br>'
            f'&bull; Absolute save rate &ge; <strong style="font-family:IBM Plex Mono;">{target_rate * 100:.2f}%</strong> (+{cur_mde_rel * 100:.1f}% relative).<br>'
            f'&bull; Per-variant sample &ge; <strong style="font-family:IBM Plex Mono;">{n_per_variant:,}</strong> accounts per arm reached.<br>'
            f'&bull; Net return &gt; ₹{CONTACT_COST_INR:.0f} unit outreach cost.'
            f'</div>'
            f'</div>'
            # Iterate card
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-left:3px solid {t.warning}; border-radius:3px; padding:10px 12px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
            f'<span style="font-weight:700; font-size:12px; color:{t.warning}; letter-spacing:0.3px;">ITERATE VARIANT (MODIFY)</span>'
            f'{render_tag(f"{cur_base_rate * 100:.1f}% &ndash; {target_rate * 100:.1f}%", "warning")}'
            f'</div>'
            f'<div style="font-size:11px; color:{t.text_primary}; line-height:1.4;">'
            f'&bull; <strong>0.050 &le; p-value &lt; 0.200</strong> with directionally positive lift.<br>'
            f'&bull; Lift observed between <strong style="font-family:IBM Plex Mono;">{cur_base_rate * 100:.1f}%</strong> and <strong style="font-family:IBM Plex Mono;">{target_rate * 100:.1f}%</strong>.<br>'
            f'&bull; Qualitative customer verbatim indicates hook resonance but copy friction.<br>'
            f'&bull; Revise copy CTA, cadence, or channel before redeployment.'
            f'</div>'
            f'</div>'
            # Stop card
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-left:3px solid {t.negative}; border-radius:3px; padding:10px 12px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
            f'<span style="font-weight:700; font-size:12px; color:{t.negative}; letter-spacing:0.3px;">STOP & ARCHIVE (HALT)</span>'
            f'{render_tag(f"&le; {cur_base_rate * 100:.1f}% Save Rate", "negative")}'
            f'</div>'
            f'<div style="font-size:11px; color:{t.text_primary}; line-height:1.4;">'
            f'&bull; <strong>P-value &ge; 0.200</strong> or negative lift (save rate &le; <strong style="font-family:IBM Plex Mono;">{cur_base_rate * 100:.1f}%</strong>).<br>'
            f'&bull; Incremental return after outreach fails to offset ₹{CONTACT_COST_INR:.0f} cost.<br>'
            f'&bull; Unsubscribe or complaint feedback &gt; 1.5%.'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    # 4. Download Pre-Registration Experiment Brief
    st.html("<div style='height: 10px;'></div>")
    brief_md = f"""# RetainAI Experiment Pre-Registration Brief
**Target Segment:** {selected_segment}  
**Date Generated:** 2026-10-31  
**Author:** Retention PM / CRM Trading Ops  

---

### 1. Primary Hypothesis
Deploying personalized intervention to **{selected_segment}** investors approaching Day 14 will increase the 60-day retained save rate from baseline **{cur_base_rate * 100:.2f}%** to at least **{target_rate * 100:.2f}%** (+{cur_mde_rel * 100:.1f}% relative MDE), generating net positive portfolio return after ₹{CONTACT_COST_INR:.0f} unit outreach cost.

### 2. Statistical Design
- **Hypothesis Test:** Two-sided two-proportion z-test
- **Significance Level (&alpha;):** 0.05 (95% confidence)
- **Statistical Power (1 - &beta;):** {int(cur_power * 100)}%
- **Baseline Save Rate:** {cur_base_rate * 100:.2f}%
- **Minimum Detectable Effect (MDE):** {cur_mde_rel * 100:.1f}% relative ({target_rate * 100:.2f}% target)
- **Sample Size Required per Arm:** {n_per_variant:,} accounts
- **Total Experiment Sample:** {n_total:,} accounts (50/50 Control vs Variant split)
- **Estimated Runtime:** {test_days} calendar days ({test_days / 7.0:.1f} weeks) at {cur_traffic:,} accounts/day

### 3. Economic Bounds
- **Investor Lifetime Value (LTV):** ₹{seg_ltv:,.0f}
- **Unit Contact Cost:** ₹{CONTACT_COST_INR:.0f}
- **Break-Even Save Rate Lift:** +{(CONTACT_COST_INR / seg_ltv) * 100:.2f} percentage points
- **Projected Net Financial Gain at MDE:** {format_rupees(projected_net_gain)}

### 4. Pre-Committed Decision Rules
1. **SHIP TO 100%:** p < 0.050, observed save rate &ge; {target_rate * 100:.2f}%, and net return exceeds ₹{CONTACT_COST_INR:.0f}/user.
2. **ITERATE VARIANT:** 0.050 &le; p < 0.200, observed lift between {cur_base_rate * 100:.1f}% and {target_rate * 100:.1f}%.
3. **STOP & ARCHIVE:** p &ge; 0.200 or save rate &le; {cur_base_rate * 100:.1f}%.
"""

    dl_col1, dl_col2 = st.columns([0.4, 0.6])
    with dl_col1:
        st.download_button(
            label="Download Experiment Brief (.md)",
            data=brief_md,
            file_name=f"experiment_brief_{selected_segment.lower()}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.html("<div style='height: 14px;'></div>")

    # 5. Live Two-Proportion Test Read-Out
    st.html(
        f'<div style="font-weight:600; font-size:13px; color:{t.text_primary}; margin-bottom:2px;">2. Two-proportion experiment result read-out</div>'
        f'<div style="font-size:11px; color:{t.text_muted}; margin-bottom:12px;">Input trial observations to calculate two-sample two-sided z-test, confidence intervals, and decision verdict</div>'
    )

    t1, t2, t3, t4 = st.columns(4, gap="medium")
    with t1:
        ctrl_successes = st.number_input("Control successes (saved)", min_value=0, max_value=200000, value=360, step=10)
    with t2:
        ctrl_n = st.number_input("Control total sample", min_value=1, max_value=500000, value=2000, step=50)
    with t3:
        var_successes = st.number_input("Variant successes (saved)", min_value=0, max_value=200000, value=440, step=10)
    with t4:
        var_n = st.number_input("Variant total sample", min_value=1, max_value=500000, value=2000, step=50)

    try:
        test_res = two_proportion_z_test(
            control_successes=ctrl_successes,
            control_total=ctrl_n,
            variant_successes=var_successes,
            variant_total=var_n,
            alpha=0.05,
        )

        p_val = test_res["p_value"]
        rel_lift = test_res["relative_change_pct"]
        abs_diff = test_res["absolute_difference"]
        ci_low = test_res["ci_lower"] * 100.0
        ci_high = test_res["ci_upper"] * 100.0

        # Decide verdict
        if test_res["is_significant"] and abs_diff > 0:
            verdict_badge = render_tag("SHIP TO 100% (WIN)", "positive")
            verdict_tone = "positive"
            verdict_text = f"Statistically significant win (p = {p_val:.4f}). Variant demonstrated a {rel_lift:+.2f}% relative improvement (+{abs_diff*100:+.2f} pts absolute). 95% CI: [{ci_low:+.2f}%, {ci_high:+.2f}%]. Meets pre-committed rollout criteria."
        elif not test_res["is_significant"] and 0.05 <= p_val < 0.20 and abs_diff > 0:
            verdict_badge = render_tag("ITERATE VARIANT (DIRECTIONAL)", "warning")
            verdict_tone = "warning"
            verdict_text = f"Directionally positive but not yet statistically significant (p = {p_val:.4f}). 95% CI [{ci_low:+.2f}%, {ci_high:+.2f}%] spans zero. Review messaging or continue gathering sample."
        else:
            verdict_badge = render_tag("STOP & ARCHIVE (INCONCLUSIVE / LOSS)", "negative")
            verdict_tone = "danger"
            verdict_text = f"Halt intervention (p = {p_val:.4f}). Variant showed no statistically significant superiority over control (rel lift: {rel_lift:+.2f}%). 95% CI: [{ci_low:+.2f}%, {ci_high:+.2f}%]."

        readout_metrics = [
            {"label": "Control save rate", "value": f"{test_res['control_rate'] * 100:.2f}%", "sub": f"{ctrl_successes:,} / {ctrl_n:,} saved", "delta": None},
            {"label": "Variant save rate", "value": f"{test_res['variant_rate'] * 100:.2f}%", "sub": f"{var_successes:,} / {var_n:,} saved", "delta": f"{abs_diff * 100:+.2f} pts", "delta_good": abs_diff > 0},
            {"label": "Relative lift", "value": f"{rel_lift:+.2f}%", "sub": f"95% CI: [{ci_low:+.2f}%, {ci_high:+.2f}%]", "delta": f"z = {test_res['z_statistic']:.2f}", "delta_good": rel_lift > 0},
            {"label": "P-value (Two-tailed)", "value": f"{p_val:.4f}", "sub": "Significance threshold &alpha;=0.05", "delta": "p < 0.05" if test_res["is_significant"] else "p &ge; 0.05", "delta_good": test_res["is_significant"]},
        ]
        render_metric_strip(readout_metrics)

        # Verdict card
        st.html(
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:12px 16px; margin-top:8px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
            f'<span style="font-weight:700; font-size:13px; color:{t.text_primary};">PROTOCOL EVALUATION VERDICT</span>'
            f'<div>{verdict_badge}</div>'
            f'</div>'
            f'<div style="font-size:12px; color:{t.text_primary}; line-height:1.5;">'
            f'{verdict_text}'
            f'</div>'
            f'</div>'
        )

    except Exception as e:
        st.error(f"Error computing two-proportion test: {e}")
