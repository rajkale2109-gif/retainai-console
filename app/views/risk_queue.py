"""Risk queue view: Master-Detail operational console for account triage and intervention ticket execution."""

from typing import Any, Dict, List, Set
import streamlit as st
import pandas as pd
import numpy as np

from app.ui import (
    get_current_theme,
    format_rupees,
    render_metric_strip,
    render_section_header,
    render_status_bar,
    render_tag,
)
from app.data import get_scores


def classify_reason_polarity(reason: str) -> str:
    """Classify behavioural signals into Raising Risk vs Protective signals."""
    r_lower = reason.lower()
    protective_keywords = [
        "high-intent",
        "watchlist additions",
        "frequent",
        "logins",
        "profitable",
        "standard",
        "48h",
    ]
    for kw in protective_keywords:
        if kw in r_lower:
            return "protective"
    return "risk"


def render() -> None:
    t = get_current_theme()

    render_section_header(
        "Risk queue",
        "Prioritized operational queue of accounts approaching day-14 checkpoint. Rank ordered by positive net expected value.",
    )

    scores_df = get_scores()
    if scores_df.empty:
        st.warning("User scores unavailable. Please run the pipeline.")
        return

    # Initialize triage session state
    if "approved_user_ids" not in st.session_state:
        st.session_state["approved_user_ids"] = set()
    if "skipped_user_ids" not in st.session_state:
        st.session_state["skipped_user_ids"] = set()
    if "snoozed_user_ids" not in st.session_state:
        st.session_state["snoozed_user_ids"] = set()
    if "selected_segment_tab" not in st.session_state:
        st.session_state["selected_segment_tab"] = "All"
    if "selected_user_id" not in st.session_state:
        st.session_state["selected_user_id"] = None

    approved_set: Set[str] = st.session_state["approved_user_ids"]
    skipped_set: Set[str] = st.session_state["skipped_user_ids"]
    snoozed_set: Set[str] = st.session_state["snoozed_user_ids"]

    # 1. Segment Tabs with live counts so no single segment dominates
    segment_counts = scores_df["segment"].value_counts().to_dict()
    tab_labels = ["All"] + sorted(list(segment_counts.keys()))

    seg_cols = st.columns(len(tab_labels))
    for idx, seg_name in enumerate(tab_labels):
        cnt_str = f"{len(scores_df):,}" if seg_name == "All" else f"{segment_counts.get(seg_name, 0):,}"
        btn_label = f"{seg_name} ({cnt_str})"
        is_active = st.session_state["selected_segment_tab"] == seg_name
        btn_type = "primary" if is_active else "secondary"

        with seg_cols[idx]:
            if st.button(btn_label, key=f"seg_tab_{seg_name}", use_container_width=True, type=btn_type):
                st.session_state["selected_segment_tab"] = seg_name
                st.rerun()

    active_seg = st.session_state["selected_segment_tab"]

    # 2. Compact Filter Toolbar
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.4, 1.4, 1.2], gap="small")

    with f_col1:
        channels = ["All"] + sorted(list(scores_df["acquisition_channel"].unique()))
        selected_channel = st.selectbox("Acquisition channel", channels, index=0)

    with f_col2:
        min_risk_pct = st.slider("Min predicted risk (%)", min_value=0, max_value=90, value=0, step=5, format="%d%%")
        min_risk = min_risk_pct / 100.0

    with f_col3:
        search_query = st.text_input("Search user ID", placeholder="e.g. 1042").strip()

    with f_col4:
        st.html("<div style='height: 24px;'></div>")
        # Export button for approved items or filtered set
        if approved_set:
            export_df = scores_df[scores_df["user_id"].astype(str).isin(approved_set)]
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"Export Approved ({len(approved_set)})",
                data=csv_data,
                file_name="retainai_approved_triage.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            export_df = scores_df[scores_df["should_contact"]]
            csv_data = export_df.head(1000).to_csv(index=False).encode("utf-8")
            st.download_button(
                "Export Filtered (CSV)",
                data=csv_data,
                file_name="retainai_risk_queue.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # Apply Filters
    filtered_df = scores_df.copy()
    if active_seg != "All":
        filtered_df = filtered_df[filtered_df["segment"] == active_seg]
    if selected_channel != "All":
        filtered_df = filtered_df[filtered_df["acquisition_channel"] == selected_channel]
    if min_risk > 0:
        filtered_df = filtered_df[filtered_df["predicted_risk"] >= min_risk]
    if search_query:
        filtered_df = filtered_df[filtered_df["user_id"].astype(str).str.contains(search_query, case=False)]

    # Sort descending by expected value
    filtered_df = filtered_df.sort_values(by="expected_value", ascending=False).reset_index(drop=True)

    # 3. Ruled Metric Strip for active selection
    total_matched = len(filtered_df)
    contactable_cnt = int(filtered_df["should_contact"].sum()) if total_matched > 0 else 0
    avg_risk = filtered_df["predicted_risk"].mean() if total_matched > 0 else 0.0
    total_ev = filtered_df["expected_value"].sum() if total_matched > 0 else 0.0

    strip_metrics = [
        {"label": f"Filtered accounts ({active_seg})", "value": f"{total_matched:,}", "sub": f"Risk >= {min_risk_pct}%"},
        {"label": "Contactable accounts", "value": f"{contactable_cnt:,}", "sub": "Net EV > ₹0"},
        {"label": "Average predicted risk", "value": f"{avg_risk * 100:.1f}%", "sub": "Out-of-fold probability"},
        {"label": "Net expected value", "value": format_rupees(total_ev, compact=True), "sub": "After ₹15 unit contact cost"},
    ]
    render_metric_strip(strip_metrics)

    if total_matched == 0:
        st.info("No accounts match the active filter criteria. Adjust your segment, channel, or risk threshold.")
        return

    # 4. Master-Detail Workstation Layout (65% Table / 35% Order Ticket Drawer)
    table_col, ticket_col = st.columns([1.3, 0.7], gap="medium")

    # Format Master Table
    display_df = filtered_df.head(200)[
        [
            "user_id",
            "segment",
            "acquisition_channel",
            "predicted_risk",
            "expected_value",
            "signup_date",
        ]
    ].copy()

    display_df["predicted_risk"] = display_df["predicted_risk"] * 100.0
    display_df["user_id"] = display_df["user_id"].apply(lambda uid: f"USR-{int(uid):05d}")

    # Determine default selected user
    selected_uid_str = st.session_state["selected_user_id"]
    default_idx = 0
    if selected_uid_str:
        matched_indices = display_df.index[display_df["user_id"] == selected_uid_str].tolist()
        if matched_indices:
            default_idx = matched_indices[0]

    with table_col:
        st.html(
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;">'
            f'<span style="font-weight:600; font-size:13px; color:{t.text_primary};">Prioritized account ledger</span>'
            f'<span style="font-size:11px; color:{t.text_muted};">Showing top 200 of {total_matched:,} | Click a row to open intervention ticket</span>'
            f'</div>'
        )

        event = st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            height=460,
            column_config={
                "user_id": st.column_config.TextColumn("Account ID", width="small"),
                "segment": st.column_config.TextColumn("Segment", width="small"),
                "acquisition_channel": st.column_config.TextColumn("Channel", width="small"),
                "predicted_risk": st.column_config.ProgressColumn(
                    "Dormancy Risk",
                    format="%.1f%%",
                    min_value=0.0,
                    max_value=100.0,
                    width="medium",
                ),
                "expected_value": st.column_config.NumberColumn(
                    "Net EV (₹)",
                    format="₹%.2f",
                    width="small",
                ),
                "signup_date": st.column_config.DateColumn("Signup Date", width="small"),
            },
        )

        # Update selected user based on row click
        if event and event.selection and event.selection.rows:
            clicked_row_idx = event.selection.rows[0]
            st.session_state["selected_user_id"] = display_df.iloc[clicked_row_idx]["user_id"]
        elif st.session_state["selected_user_id"] is None and len(display_df) > 0:
            st.session_state["selected_user_id"] = display_df.iloc[0]["user_id"]

    # Retrieve selected row data
    curr_selected_uid = st.session_state["selected_user_id"]
    raw_uid = int(curr_selected_uid.replace("USR-", "")) if curr_selected_uid else int(filtered_df.iloc[0]["user_id"])
    user_record = scores_df[scores_df["user_id"] == raw_uid].iloc[0]

    # 5. Detail View: Intervention Ticket Drawer (Modelled on Broker Order Ticket)
    with ticket_col:
        # Current index in display_df & Touch-Friendly Account Stepper
        current_acc_str = f"USR-{raw_uid:05d}"
        acc_list = display_df["user_id"].tolist()
        curr_acc_idx = acc_list.index(current_acc_str) if current_acc_str in acc_list else 0

        nav_prev_col, nav_info_col, nav_next_col = st.columns([1, 1.8, 1], gap="small")
        with nav_prev_col:
            if st.button("◀ Prev", key=f"prev_acc_btn_{raw_uid}", use_container_width=True, disabled=(curr_acc_idx == 0)):
                st.session_state["selected_user_id"] = acc_list[curr_acc_idx - 1]
                st.rerun()
        with nav_info_col:
            st.html(f'<div style="text-align:center; font-size:11px; color:{t.text_muted}; padding-top:6px; font-variant-numeric:tabular-nums;">Account {curr_acc_idx + 1} of {len(acc_list)}</div>')
        with nav_next_col:
            if st.button("Next ▶", key=f"next_acc_btn_{raw_uid}", use_container_width=True, disabled=(curr_acc_idx >= len(acc_list) - 1)):
                st.session_state["selected_user_id"] = acc_list[curr_acc_idx + 1]
                st.rerun()

        u_risk_pct = user_record["predicted_risk"] * 100.0
        u_ev = user_record["expected_value"]
        u_seg = user_record["segment"]
        u_chan = user_record["acquisition_channel"]
        u_signup = user_record["signup_date"]
        u_status_tag = "APPROVED" if str(raw_uid) in approved_set else ("SKIPPED" if str(raw_uid) in skipped_set else ("SNOOZED" if str(raw_uid) in snoozed_set else "PENDING"))
        tag_variant = "positive" if u_status_tag == "APPROVED" else ("negative" if u_status_tag == "SKIPPED" else ("warning" if u_status_tag == "SNOOZED" else "neutral"))

        # Ticket Container
        ticket_header_html = (
            f'<div style="background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:12px; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid {t.border}; padding-bottom:6px; margin-bottom:8px;">'
            f'<div>'
            f'<span style="font-family:var(--font-mono); font-weight:700; font-size:14px; color:{t.text_primary};">USR-{raw_uid:05d}</span>'
            f'<span style="margin-left:6px;">{render_tag(u_seg, "accent")}</span>'
            f'</div>'
            f'<div>{render_tag(u_status_tag, tag_variant)}</div>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; font-size:11px; color:{t.text_muted}; margin-bottom:10px;">'
            f'<span>Signup: <strong>{u_signup}</strong></span>'
            f'<span>Channel: <strong>{u_chan}</strong></span>'
            f'<span>LTV: <strong>₹{user_record["lifetime_value"]:,.0f}</strong></span>'
            f'</div>'
            f'<div style="background:{t.raised}; border:1px solid {t.border}; border-radius:3px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<div style="font-size:10px; color:{t.text_muted};">PREDICTED DORMANCY</div>'
            f'<div style="font-size:18px; font-weight:700; color:{t.negative if u_risk_pct >= 40 else t.warning};">{u_risk_pct:.1f}%</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-size:10px; color:{t.text_muted};">NET EXPECTED RETURN</div>'
            f'<div style="font-size:18px; font-weight:700; color:{t.positive if u_ev > 0 else t.negative};">{format_rupees(u_ev)}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.html(ticket_header_html)

        # Behavioural Drivers with Polarity Distinction (FIX FOR ISSUE n)
        raw_reasons = [user_record["top_reason_1"], user_record["top_reason_2"], user_record["top_reason_3"]]
        raising_drivers = [r for r in raw_reasons if classify_reason_polarity(r) == "risk" and r != "Standard onboarding lifecycle activity"]
        protective_signals = [r for r in raw_reasons if classify_reason_polarity(r) == "protective" and r != "Standard onboarding lifecycle activity"]

        drivers_html = f'<div style="background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:10px 12px; margin-bottom:8px; font-size:11px;">'
        drivers_html += f'<div style="font-weight:600; color:{t.text_muted}; margin-bottom:4px; font-size:10px; letter-spacing:0.5px;">BEHAVIOURAL SIGNALS (DAYS 0-14)</div>'

        if raising_drivers:
            drivers_html += f'<div style="color:{t.negative}; font-weight:600; margin-top:4px;">▲ Raising Dormancy Risk:</div>'
            for rd in raising_drivers:
                drivers_html += f'<div style="color:{t.text_primary}; margin-left:8px; line-height:1.4;">• {rd}</div>'

        if protective_signals:
            drivers_html += f'<div style="color:{t.positive}; font-weight:600; margin-top:6px;">▼ Protective Signals:</div>'
            for ps in protective_signals:
                drivers_html += f'<div style="color:{t.text_primary}; margin-left:8px; line-height:1.4;">• {ps}</div>'

        if not raising_drivers and not protective_signals:
            drivers_html += f'<div style="color:{t.text_muted}; margin-left:8px;">• Standard lifecycle engagement trajectory</div>'

        drivers_html += '</div>'
        st.html(drivers_html)

        # Playbook Specification & Editable Template
        st.html(
            f'<div style="font-weight:600; font-size:11px; color:{t.text_muted}; margin-bottom:2px; letter-spacing:0.5px;">RECOMMENDED INTERVENTION</div>'
            f'<div style="font-size:11px; color:{t.text_primary}; background:{t.panel}; border:1px solid {t.border}; padding:6px 10px; border-radius:3px; margin-bottom:6px;">'
            f'<strong>Action:</strong> {user_record["recommended_action"]}<br>'
            f'<strong>Channel:</strong> {user_record["recommended_channel"]} | <strong>Save Rate:</strong> {user_record["save_rate"] * 100:.0f}%'
            f'</div>'
        )

        editable_message = st.text_area(
            "Outreach copy template (editable)",
            value=user_record["recommended_message"],
            height=70,
            label_visibility="collapsed",
            key=f"msg_box_{raw_uid}",
        )

        # Operational Triage Action Buttons
        btn_c1, btn_c2, btn_c3 = st.columns(3, gap="small")
        with btn_c1:
            if st.button("✔ Approve", key=f"btn_app_{raw_uid}", use_container_width=True, type="primary"):
                approved_set.add(str(raw_uid))
                skipped_set.discard(str(raw_uid))
                snoozed_set.discard(str(raw_uid))
                st.rerun()
        with btn_c2:
            if st.button("✖ Skip", key=f"btn_skip_{raw_uid}", use_container_width=True):
                skipped_set.add(str(raw_uid))
                approved_set.discard(str(raw_uid))
                snoozed_set.discard(str(raw_uid))
                st.rerun()
        with btn_c3:
            if st.button("⏱ Snooze", key=f"btn_snz_{raw_uid}", use_container_width=True):
                snoozed_set.add(str(raw_uid))
                approved_set.discard(str(raw_uid))
                skipped_set.discard(str(raw_uid))
                st.rerun()

        # Triage Progress & Simulation Notice
        st.html(
            f'<div style="font-size:11px; color:{t.text_muted}; margin-top:8px; padding-top:6px; border-top:1px solid {t.border};">'
            f'<strong>Triage Progress:</strong> <span style="color:{t.positive};">{len(approved_set)} Approved</span> | '
            f'<span style="color:{t.negative};">{len(skipped_set)} Skipped</span> | '
            f'<span style="color:{t.warning};">{len(snoozed_set)} Snoozed</span>'
            f'<div style="font-size:10px; color:{t.text_muted}; margin-top:3px;">Simulation Mode: Approvals are logged in session; no external calls/messages are dispatched.</div>'
            f'</div>'
        )

    # 6. Bottom Status Line
    render_status_bar(
        rows_shown=total_matched,
        active_filters=f"Segment: {active_seg} | Channel: {selected_channel} | Min Risk: {min_risk_pct}%",
        approved_count=len(approved_set),
    )
