"""Risk queue view: User filtering, ranked queue, CSV export, and individual driver inspection."""

import streamlit as st
import pandas as pd

from app.ui import (
    COLOR_BORDER,
    COLOR_MUTED_INK,
    COLOR_PETROL,
    COLOR_SURFACE,
    format_rupees,
    render_callout,
    render_metric_strip,
    render_section_header,
)
from app.data import get_scores


def render() -> None:
    render_section_header(
        "Risk queue",
        "Ranked list of users at risk of dormancy, prioritized by positive net expected return.",
    )

    scores_df = get_scores()
    if scores_df.empty:
        st.warning("User scores unavailable. Please run the pipeline.")
        return

    # Filter Controls
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1.2])

    with filter_col1:
        segments = ["All"] + sorted(list(scores_df["segment"].unique()))
        selected_segment = st.selectbox("Segment", segments, index=0)

    with filter_col2:
        channels = ["All"] + sorted(list(scores_df["acquisition_channel"].unique()))
        selected_channel = st.selectbox("Acquisition channel", channels, index=0)

    with filter_col3:
        min_risk = st.slider("Minimum predicted risk", min_value=0.0, max_value=1.0, value=0.35, step=0.05)

    # Apply Filters
    filtered_df = scores_df.copy()
    if selected_segment != "All":
        filtered_df = filtered_df[filtered_df["segment"] == selected_segment]
    if selected_channel != "All":
        filtered_df = filtered_df[filtered_df["acquisition_channel"] == selected_channel]
    filtered_df = filtered_df[filtered_df["predicted_risk"] >= min_risk]

    # Sort descending by expected value
    filtered_df = filtered_df.sort_values(by="expected_value", ascending=False).reset_index(drop=True)

    # Metric Strip for Filtered Selection
    total_matched = len(filtered_df)
    contactable_cnt = int(filtered_df["should_contact"].sum()) if total_matched > 0 else 0
    avg_risk = filtered_df["predicted_risk"].mean() if total_matched > 0 else 0.0
    total_ev = filtered_df["expected_value"].sum() if total_matched > 0 else 0.0

    strip_metrics = [
        {"label": "Matching users", "value": f"{total_matched:,}", "sub": f"Risk >= {min_risk:.2f}"},
        {"label": "Contactable users", "value": f"{contactable_cnt:,}", "sub": "Net EV > 0"},
        {"label": "Average risk", "value": f"{avg_risk * 100:.1f}%", "sub": "Out-of-fold probability"},
        {"label": "Total net expected value", "value": format_rupees(total_ev), "sub": "After ₹15 contact cost"},
    ]
    render_metric_strip(strip_metrics)

    # CSV Export Button
    export_cols = [
        "user_id",
        "signup_date",
        "acquisition_channel",
        "segment",
        "predicted_risk",
        "expected_value",
        "should_contact",
        "recommended_channel",
        "recommended_action",
        "recommended_message",
        "top_reason_1",
        "top_reason_2",
        "top_reason_3",
    ]
    csv_data = filtered_df[export_cols].to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Export filtered queue (CSV)",
        data=csv_data,
        file_name="retainai_risk_queue.csv",
        mime="text/csv",
    )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Display Ranked Table
    display_df = filtered_df[
        [
            "user_id",
            "signup_date",
            "acquisition_channel",
            "segment",
            "predicted_risk",
            "expected_value",
            "should_contact",
            "recommended_channel",
        ]
    ].copy()

    display_df.columns = [
        "User ID",
        "Signup date",
        "Channel",
        "Segment",
        "Predicted risk",
        "Net EV (₹)",
        "Contact",
        "Outreach channel",
    ]
    display_df["Predicted risk"] = display_df["Predicted risk"].apply(lambda r: f"{r * 100:.1f}%")
    display_df["Net EV (₹)"] = display_df["Net EV (₹)"].apply(lambda v: format_rupees(v))
    display_df["Contact"] = display_df["Contact"].apply(lambda c: "Yes" if c else "No")

    st.dataframe(
        display_df.head(100),
        use_container_width=True,
        hide_index=True,
        height=340,
    )
    if total_matched > 100:
        st.markdown(f"<p style='color: {COLOR_MUTED_INK}; font-size: 11px; margin-top: 4px;'>Showing top 100 of {total_matched:,} users. Export CSV to download the complete queue.</p>", unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Per-User Reason and Message Inspection
    st.markdown("<p style='font-weight: 600; font-size: 15px; margin-bottom: 2px;'>Inspect individual user</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5A6572; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>Review risk factors and personalized intervention copy for any selected user.</p>", unsafe_allow_html=True)

    if total_matched > 0:
        candidate_ids = filtered_df["user_id"].head(50).tolist()
        inspect_id = st.selectbox("Select user ID to inspect", candidate_ids, index=0)

        user_row = filtered_df[filtered_df["user_id"] == inspect_id].iloc[0]

        u_col1, u_col2 = st.columns([1, 1], gap="medium")

        with u_col1:
            st.markdown(
                f"""
                <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 16px;">
                    <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px;">User profile & diagnostics</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>User ID:</strong> {user_row['user_id']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Signup date:</strong> {user_row['signup_date']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Segment:</strong> {user_row['segment']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Acquisition channel:</strong> {user_row['acquisition_channel']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Predicted dormancy risk:</strong> {user_row['predicted_risk'] * 100:.1f}%</div>
                    <div style="font-size: 12px;"><strong>Net expected value:</strong> {format_rupees(user_row['expected_value'])}</div>
                    <div style="margin-top: 12px; font-weight: 600; font-size: 12px; color: {COLOR_MUTED_INK};">Key risk drivers (days 0-14):</div>
                    <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 12px;">
                        <li>{user_row['top_reason_1']}</li>
                        <li>{user_row['top_reason_2']}</li>
                        <li>{user_row['top_reason_3']}</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with u_col2:
            st.markdown(
                f"""
                <div style="background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 16px;">
                    <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px;">Recommended playbook intervention</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Action:</strong> {user_row['recommended_action']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Delivery channel:</strong> {user_row['recommended_channel']}</div>
                    <div style="font-size: 12px; margin-bottom: 4px;"><strong>Assumed save rate:</strong> {user_row['save_rate'] * 100:.1f}% | <strong>LTV:</strong> {format_rupees(user_row['lifetime_value'])}</div>
                    <div style="font-size: 12px; margin-bottom: 12px;"><strong>Contact recommendation:</strong> <span style="font-weight: 600; color: {'#0E5A6B' if user_row['should_contact'] else '#A63D40'};">{'Proceed (EV > 0)' if user_row['should_contact'] else 'Do not contact (EV <= 0)'}</span></div>
                    <div style="font-weight: 600; font-size: 12px; color: {COLOR_MUTED_INK}; margin-bottom: 4px;">Outreach message template:</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_callout(f'"{user_row["recommended_message"]}"', tone="neutral")
    else:
        st.info("No users match the selected filters.")
