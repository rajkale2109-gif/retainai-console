"""UI design system, tokens, formatting, and components for RetainAI.

Design Rules (from SPEC.md):
- Cool grey canvas #F5F6F8, white surfaces, ink #17212B, one petrol accent #0E5A6B,
  muted red #A63D40 and amber #B7791F only for risk.
- One typeface: Public Sans. Sentence case everywhere.
- Key figures in one ruled strip, not a row of identical cards.
- No emoji, gradients, drop shadows, all-caps labels, or decorative animation.
- Charts: no toolbar, light gridlines, direct data labels.
- Rupees use Indian digit grouping. Empty states say what to do next. Plain verbs.
"""

from typing import Any, Dict, List, Optional
import streamlit as st
import plotly.graph_objects as go


# Design Tokens
COLOR_CANVAS = "#F5F6F8"
COLOR_SURFACE = "#FFFFFF"
COLOR_INK = "#17212B"
COLOR_MUTED_INK = "#5A6572"
COLOR_BORDER = "#E2E5E9"
COLOR_PETROL = "#0E5A6B"
COLOR_MUTED_RED = "#A63D40"
COLOR_AMBER = "#B7791F"
COLOR_GRIDLINE = "#ECEEF1"
FONT_FAMILY = "'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def inject_global_styles() -> None:
    """Inject Public Sans typography, clean neutral styling, and strip default decorations."""
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, .stText, p, div, span, h1, h2, h3, h4, h5, h6 {{
        font-family: {FONT_FAMILY} !important;
        color: {COLOR_INK};
    }}

    /* Canvas background */
    .stApp {{
        background-color: {COLOR_CANVAS};
    }}

    /* Remove drop shadows and border radii gradients */
    div[data-testid="stMetric"], .stMetric, div[data-testid="stExpander"] {{
        background-color: {COLOR_SURFACE} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 2px !important;
        box-shadow: none !important;
    }}

    /* Global sentence case and remove all-caps transforms */
    button, [role="tab"], th, label, .stSelectbox label, .stSlider label {{
        text-transform: none !important;
        letter-spacing: normal !important;
        font-family: {FONT_FAMILY} !important;
    }}

    /* Sidebar minimal navigation styling */
    section[data-testid="stSidebar"] {{
        background-color: {COLOR_SURFACE};
        border-right: 1px solid {COLOR_BORDER};
    }}

    /* Buttons: Petrol accent, no shadows */
    .stButton > button {{
        background-color: {COLOR_PETROL} !important;
        color: #FFFFFF !important;
        border: 1px solid {COLOR_PETROL} !important;
        border-radius: 2px !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 6px 14px !important;
    }}
    .stButton > button:hover {{
        background-color: #0B4653 !important;
        border-color: #0B4653 !important;
        color: #FFFFFF !important;
    }}

    /* Ruled metric strip */
    .metric-strip-container {{
        display: flex;
        flex-direction: row;
        width: 100%;
        background-color: {COLOR_SURFACE};
        border-top: 1px solid {COLOR_BORDER};
        border-bottom: 1px solid {COLOR_BORDER};
        margin: 16px 0 24px 0;
        padding: 14px 0;
    }}
    .metric-strip-item {{
        flex: 1;
        padding: 0 20px;
        border-right: 1px solid {COLOR_BORDER};
    }}
    .metric-strip-item:last-child {{
        border-right: none;
    }}
    .metric-strip-label {{
        font-size: 12px;
        color: {COLOR_MUTED_INK};
        margin-bottom: 4px;
        font-weight: 500;
    }}
    .metric-strip-value {{
        font-size: 24px;
        font-weight: 600;
        color: {COLOR_INK};
        line-height: 1.2;
    }}
    .metric-strip-sub {{
        font-size: 11px;
        color: {COLOR_MUTED_INK};
        margin-top: 3px;
    }}

    /* Simple Callout */
    .callout-box {{
        padding: 12px 16px;
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-left: 3px solid {COLOR_PETROL};
        margin: 12px 0;
        font-size: 13px;
        color: {COLOR_INK};
    }}
    .callout-box.warning {{
        border-left-color: {COLOR_AMBER};
    }}
    .callout-box.danger {{
        border-left-color: {COLOR_MUTED_RED};
    }}

    /* Table styling */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {COLOR_BORDER};
        background-color: {COLOR_SURFACE};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def format_rupees(amount: float, compact: bool = False) -> str:
    """Format numeric values into Indian Rupee notation with appropriate comma grouping."""
    if amount is None or (isinstance(amount, float) and (amount != amount)):
        return "₹0"

    sign = "-" if amount < 0 else ""
    abs_amt = abs(amount)

    if compact:
        if abs_amt >= 10_000_000:
            return f"{sign}₹{abs_amt / 10_000_000:.2f}Cr"
        if abs_amt >= 100_000:
            return f"{sign}₹{abs_amt / 100_000:.2f}L"
        if abs_amt >= 1_000:
            return f"{sign}₹{abs_amt / 1_000:.1f}k"

    # Exact Indian comma grouping (last 3 digits, then groups of 2)
    int_part = int(round(abs_amt))
    s = str(int_part)
    if len(s) <= 3:
        formatted = s
    else:
        last_three = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last_three

    return f"{sign}₹{formatted}"


def render_metric_strip(metrics: List[Dict[str, Any]]) -> None:
    """Render key figures in one ruled strip across the screen."""
    items_html = []
    for m in metrics:
        label = m.get("label", "")
        value = m.get("value", "")
        sub = m.get("sub", "")
        sub_html = f'<div class="metric-strip-sub">{sub}</div>' if sub else ""
        items_html.append(f"""
            <div class="metric-strip-item">
                <div class="metric-strip-label">{label}</div>
                <div class="metric-strip-value">{value}</div>
                {sub_html}
            </div>
        """)

    strip_html = f"""
        <div class="metric-strip-container">
            {"".join(items_html)}
        </div>
    """
    st.markdown(strip_html, unsafe_allow_html=True)


def render_section_header(title: str, description: Optional[str] = None) -> None:
    """Render a clean, plain sentence-case section header."""
    st.markdown(f"<h3 style='margin-bottom: 2px; font-weight: 600; font-size: 18px;'>{title}</h3>", unsafe_allow_html=True)
    if description:
        st.markdown(f"<p style='color: {COLOR_MUTED_INK}; font-size: 13px; margin-top: 0; margin-bottom: 16px;'>{description}</p>", unsafe_allow_html=True)


def render_callout(text: str, tone: str = "neutral") -> None:
    """Render a clean callout box with plain verbs and no emoji."""
    cls_name = "callout-box"
    if tone in ["warning", "danger"]:
        cls_name += f" {tone}"
    st.markdown(f'<div class="{cls_name}">{text}</div>', unsafe_allow_html=True)


def render_empty_state(title: str, message: str, command: Optional[str] = None) -> None:
    """Render an informative empty state explaining what to do next."""
    cmd_html = f"<div style='margin-top: 14px; font-family: monospace; background: #EEF0F3; padding: 8px 12px; display: inline-block; font-size: 13px;'>{command}</div>" if command else ""
    empty_html = f"""
    <div style="background-color: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; padding: 36px 24px; text-align: center; margin: 24px 0;">
        <h4 style="margin: 0 0 8px 0; font-weight: 600; font-size: 16px;">{title}</h4>
        <p style="color: {COLOR_MUTED_INK}; font-size: 14px; margin: 0; max-width: 540px; margin: 0 auto;">{message}</p>
        {cmd_html}
    </div>
    """
    st.markdown(empty_html, unsafe_allow_html=True)


def apply_chart_theme(fig: go.Figure, height: int = 380) -> go.Figure:
    """Apply minimal styling rules to Plotly figures.

    Rules: No toolbar, light gridlines, clean margins, Public Sans font.
    """
    fig.update_layout(
        font=dict(family="Public Sans, -apple-system, sans-serif", color=COLOR_INK, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=16, r=16, t=28, b=24),
        height=height,
        hoverlabel=dict(
            bgcolor=COLOR_SURFACE,
            font_size=12,
            font_family="Public Sans, -apple-system, sans-serif",
            bordercolor=COLOR_BORDER,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color=COLOR_MUTED_INK),
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=COLOR_GRIDLINE,
        gridwidth=1,
        linecolor=COLOR_BORDER,
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=11, color=COLOR_MUTED_INK),
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLOR_GRIDLINE,
        gridwidth=1,
        linecolor=COLOR_BORDER,
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=11, color=COLOR_MUTED_INK),
    )

    return fig
