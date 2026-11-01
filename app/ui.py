"""RetainAI: Terminal Design System, Tokens, Typography, and Component Architecture.

Institutional-grade styling inspired by Zerodha Kite, Upstox Pro, Groww Web, and Bloomberg Terminal.
Supports Dark Theme (Default) and Light Theme with instant toggling.
"""

from typing import Any, Dict, List, Optional
import streamlit as st
import plotly.graph_objects as go


# ==============================================================================
# 1. DESIGN TOKENS
# ==============================================================================

class ThemeTokens:
    def __init__(
        self,
        name: str,
        canvas: str,
        panel: str,
        raised: str,
        border: str,
        border_subtle: str,
        text_primary: str,
        text_muted: str,
        accent: str,
        positive: str,
        negative: str,
        warning: str,
        mono_id: str,
        gridline: str,
    ):
        self.name = name
        self.canvas = canvas
        self.panel = panel
        self.raised = raised
        self.border = border
        self.border_subtle = border_subtle
        self.text_primary = text_primary
        self.text_muted = text_muted
        self.accent = accent
        self.positive = positive
        self.negative = negative
        self.warning = warning
        self.mono_id = mono_id
        self.gridline = gridline


DARK_THEME = ThemeTokens(
    name="dark",
    canvas="#0E1217",
    panel="#151B23",
    raised="#1B232D",
    border="#263040",
    border_subtle="#1B232D",
    text_primary="#E6EAF0",
    text_muted="#8C98A8",
    accent="#00A389",
    positive="#10B981",
    negative="#EF4444",
    warning="#F59E0B",
    mono_id="#94A3B8",
    gridline="#1E2734",
)

LIGHT_THEME = ThemeTokens(
    name="light",
    canvas="#F4F5F7",
    panel="#FFFFFF",
    raised="#F8F9FA",
    border="#DDE2E8",
    border_subtle="#ECEEF1",
    text_primary="#17212B",
    text_muted="#5A6572",
    accent="#0E5A6B",
    positive="#059669",
    negative="#DC2626",
    warning="#D97706",
    mono_id="#475569",
    gridline="#ECEEF1",
)


def get_current_theme() -> ThemeTokens:
    """Retrieve active theme tokens from query parameters or session state."""
    param_theme = st.query_params.get("theme")
    if param_theme in ["dark", "light"]:
        st.session_state["retainai_theme"] = param_theme

    theme_name = st.session_state.get("retainai_theme", "dark")
    return DARK_THEME if theme_name == "dark" else LIGHT_THEME


# Convenience module-level token aliases for active theme
tokens = get_current_theme()

# Backward compatibility aliases for existing views (Phase 2 & 3 refactoring)
COLOR_CANVAS = DARK_THEME.canvas
COLOR_SURFACE = DARK_THEME.panel
COLOR_INK = DARK_THEME.text_primary
COLOR_MUTED_INK = DARK_THEME.text_muted
COLOR_BORDER = DARK_THEME.border
COLOR_PETROL = DARK_THEME.accent
COLOR_MUTED_RED = DARK_THEME.negative
COLOR_AMBER = DARK_THEME.warning
COLOR_GRIDLINE = DARK_THEME.gridline
FONT_FAMILY = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


# ==============================================================================
# 2. GLOBAL STYLES & TYPOGRAPHY INJECTION
# ==============================================================================

def inject_terminal_styles(theme: Optional[ThemeTokens] = None) -> None:
    """Inject IBM Plex Sans typography, terminal CSS variables, and layout resets."""
    t = theme or get_current_theme()

    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {{
    --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
    --color-canvas: {t.canvas};
    --color-panel: {t.panel};
    --color-raised: {t.raised};
    --color-border: {t.border};
    --color-border-subtle: {t.border_subtle};
    --color-text-primary: {t.text_primary};
    --color-text-muted: {t.text_muted};
    --color-accent: {t.accent};
    --color-positive: {t.positive};
    --color-negative: {t.negative};
    --color-warning: {t.warning};
}}

/* Global resets & Tabular Figures */
html, body, .stApp, .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, input, button, select, textarea {{
    font-family: var(--font-sans) !important;
    font-variant-numeric: tabular-nums !important;
    color: var(--color-text-primary);
}}

[data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, .material-icons {{
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}

.stApp {{
    background-color: var(--color-canvas);
}}

/* Header styling: transparent background, keep sidebar collapse toggle accessible */
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 38px !important;
    visibility: visible !important;
    z-index: 9999 !important;
}}

[data-testid="collapsedControl"] {{
    visibility: visible !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    top: 6px !important;
    left: 6px !important;
    z-index: 10000 !important;
    background: var(--color-panel) !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 4px !important;
    color: var(--color-text-primary) !important;
    width: 32px !important;
    height: 32px !important;
}}

footer, #MainMenu {{
    visibility: hidden !important;
    height: 0px !important;
}}

/* Sidebar / Left Rail */
section[data-testid="stSidebar"] {{
    background-color: var(--color-panel) !important;
    border-right: 1px solid var(--color-border) !important;
    padding-top: 12px !important;
}}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
    gap: 0.25rem !important;
}}

/* Left Rail Navigation: Remove Radio Circles, Style as Terminal Tabs */
div[data-testid="stRadio"] div[role="radiogroup"] label {{
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 7px 12px !important;
    margin: 2px 0 !important;
    border-radius: 3px !important;
    border-left: 3px solid transparent !important;
    cursor: pointer !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--color-text-muted) !important;
    background-color: transparent !important;
    transition: background-color 0.1s ease, color 0.1s ease;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label:hover {{
    background-color: var(--color-raised) !important;
    color: var(--color-text-primary) !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"],
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background-color: var(--color-raised) !important;
    border-left: 3px solid var(--color-accent) !important;
    color: var(--color-text-primary) !important;
    font-weight: 600 !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-of-type,
div[data-testid="stRadio"] div[role="radiogroup"] [data-baseweb="radio"],
div[data-testid="stRadio"] div[role="radiogroup"] label [aria-hidden="true"],
div[data-testid="stRadio"] div[role="radiogroup"] label svg,
div[data-testid="stRadio"] div[role="radiogroup"] label span[data-testid="stRadioInput"],
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label > span:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label input[type="radio"] {{
    display: none !important;
}}

div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {{
    padding-left: 0px !important;
}}

/* Inputs, Selectboxes, and Sliders */
div[data-baseweb="select"] > div {{
    background-color: var(--color-panel) !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 3px !important;
    color: var(--color-text-primary) !important;
    font-size: 13px !important;
}}

input, .stTextInput > div > div > input {{
    background-color: var(--color-panel) !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 3px !important;
    color: var(--color-text-primary) !important;
    font-size: 13px !important;
}}

/* DataFrames */
div[data-testid="stDataFrame"] {{
    border: 1px solid var(--color-border) !important;
    border-radius: 3px !important;
    background-color: var(--color-panel) !important;
}}

/* Segmented Control Styling */
div[data-testid="stSegmentedControl"] {{
    background-color: var(--color-panel) !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 4px !important;
    padding: 3px !important;
}}
div[data-testid="stSegmentedControl"] button {{
    border: none !important;
    border-radius: 3px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--color-text-muted) !important;
    background-color: transparent !important;
    transition: background-color 0.15s ease, color 0.15s ease !important;
}}
div[data-testid="stSegmentedControl"] button:hover {{
    color: var(--color-text-primary) !important;
    background-color: var(--color-raised) !important;
}}
div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[data-checked="true"] {{
    background-color: var(--color-accent) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}}

/* Primary Buttons */
.stButton > button {{
    background-color: var(--color-accent) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--color-accent) !important;
    border-radius: 3px !important;
    box-shadow: none !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    padding: 5px 12px !important;
}}

.stButton > button:hover {{
    opacity: 0.9 !important;
}}

/* Institutional Terminal Left Rail Navigation Buttons */
section[data-testid="stSidebar"] .stButton > button {{
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-left: 3px solid transparent !important;
    color: var(--color-text-muted) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 6px 10px !important;
    font-size: 12px !important;
    border-radius: 3px !important;
    font-weight: 500 !important;
    margin: 1px 0 !important;
}}

section[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: var(--color-raised) !important;
    color: var(--color-text-primary) !important;
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background-color: var(--color-raised) !important;
    border-left: 3px solid var(--color-accent) !important;
    border-top: 1px solid transparent !important;
    border-right: 1px solid transparent !important;
    border-bottom: 1px solid transparent !important;
    color: var(--color-text-primary) !important;
    font-weight: 600 !important;
}}

/* Custom scrollbars */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: var(--color-canvas);
}}
::-webkit-scrollbar-thumb {{
    background: var(--color-border);
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: var(--color-text-muted);
}}

/* ==========================================================================
   MOBILE & RESPONSIVE ADAPTATIONS
   ========================================================================== */

/* Mobile & Tablet Navigation Strip */
@media (min-width: 1024px) {{
    .terminal-mobile-nav-container {{
        display: none !important;
    }}
}}

@media (max-width: 1023px) {{
    .terminal-mobile-nav-container {{
        display: block !important;
        margin-top: 4px !important;
        margin-bottom: 12px !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
    }}
    .terminal-mobile-nav-container::-webkit-scrollbar {{
        display: none !important;
    }}
    .terminal-mobile-nav-container div[data-testid="stSegmentedControl"] {{
        display: inline-flex !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        min-width: max-content !important;
        padding: 3px !important;
    }}
    .terminal-mobile-nav-container button {{
        flex: 0 0 auto !important;
        min-height: 38px !important;
        padding: 6px 14px !important;
        font-size: 12px !important;
    }}
}}

/* Smartphone Adjustments (<= 768px) */
@media (max-width: 768px) {{
    /* Responsive block container padding */
    .main .block-container {{
        padding-top: 0.5rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 100% !important;
    }}

    /* Metric Strip 2-Column Grid on Mobile */
    .terminal-metric-strip {{
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 1px !important;
        background: var(--color-border) !important;
        margin: 8px 0 12px 0 !important;
    }}
    .terminal-metric-item {{
        border-right: none !important;
        background: var(--color-panel) !important;
        padding: 8px 10px !important;
        min-width: 0 !important;
    }}
    .terminal-metric-item:nth-child(5) {{
        grid-column: span 2 !important;
    }}
    .terminal-metric-item div:nth-child(2) {{
        font-size: 18px !important;
    }}

    /* Ticker scrollable bar on mobile */
    .terminal-top-ticker {{
        gap: 8px !important;
        font-size: 10px !important;
        padding: 4px 8px !important;
        margin-top: 3px !important;
    }}

    /* Mobile Status Bar */
    .terminal-status-bar {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 4px !important;
        padding: 6px 10px !important;
    }}
    .terminal-status-left {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }}
    .terminal-status-right {{
        display: none !important;
    }}

    /* Touch Targets */
    .stButton > button {{
        min-height: 38px !important;
        font-size: 13px !important;
    }}
    input, textarea, select {{
        font-size: 14px !important;
    }}

    /* Responsive Plotly Charts */
    .js-plotly-plot {{
        width: 100% !important;
    }}

    /* Segmented Control scrollable */
    div[data-testid="stSegmentedControl"] {{
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }}
}}
</style>
"""
    st.html(css)


# ==============================================================================
# 3. GLOBAL SHELL COMPONENTS (TOP BAR, LEFT RAIL, STATUS LINE)
# ==============================================================================

def render_top_bar(current_page: str) -> None:
    """Render slim global system top bar with metadata ticker and theme toggle."""
    t = get_current_theme()
    other_theme = "light" if t.name == "dark" else "dark"
    theme_btn_label = "☀ Light" if t.name == "dark" else "☾ Dark"

    col_brand, col_ticker, col_toggle = st.columns([1.8, 6.2, 1.0], gap="small")

    with col_brand:
        st.html(
            f'<div style="display:flex; align-items:baseline; gap:8px; padding-top:4px;">'
            f'<span style="font-weight:700; font-size:16px; color:{t.text_primary}; letter-spacing:-0.4px;">RetainAI</span>'
            f'<span style="font-size:10px; font-family:var(--font-mono); background:{t.raised}; border:1px solid {t.border}; padding:1px 5px; border-radius:2px; color:{t.accent};">TERMINAL v1.0</span>'
            f'</div>'
        )

    with col_ticker:
        st.html(
            f'<div class="terminal-top-ticker" style="display:flex; align-items:center; gap:14px; font-size:11px; color:{t.text_muted}; background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:5px 10px; margin-top:1px; overflow-x:auto; white-space:nowrap;">'
            f'<div><strong>COHORT:</strong> 2025 Jan-Dec (20k)</div>'
            f'<div style="color:{t.border};">|</div>'
            f'<div><strong>PREDICTION:</strong> Day 14</div>'
            f'<div style="color:{t.border};">|</div>'
            f'<div><strong>MODEL:</strong> HistGB (0.693)</div>'
            f'<div style="color:{t.border};">|</div>'
            f'<div><strong>AS-OF:</strong> 2025-12-31</div>'
            f'<div style="color:{t.border};">|</div>'
            f'<div><strong>PAGE:</strong> {current_page}</div>'
            f'</div>'
        )

    with col_toggle:
        if st.button(theme_btn_label, key="theme_toggle_btn", use_container_width=True):
            st.session_state["retainai_theme"] = other_theme
            st.rerun()


def render_mobile_nav(active_page: str) -> None:
    """Render a mobile-optimized thumb navigation bar that displays on small viewports."""
    page_map = {
        "Overview": "Overview",
        "Risk queue": "Risk Queue",
        "Segments and playbook": "Playbook",
        "Experiment planner": "A/B Planner",
        "Model and threshold": "Model & Cutoff",
    }
    st.html('<div class="terminal-mobile-nav-container">')
    selected = st.segmented_control(
        "Mobile Navigation",
        options=list(page_map.keys()),
        format_func=lambda k: page_map.get(k, k),
        default=active_page,
        key="mobile_nav_segmented_control",
        label_visibility="collapsed",
    )
    st.html('</div>')

    if selected and selected != active_page:
        st.session_state["current_nav_page"] = selected
        st.query_params["page"] = selected
        st.rerun()


def render_sidebar_rail() -> str:
    """Render terminal grouped left rail navigation with zero radio circles."""
    t = get_current_theme()

    st.sidebar.html(
        f'<div style="padding: 4px 8px 12px 8px; border-bottom: 1px solid {t.border}; margin-bottom: 8px;">'
        f'<div style="font-size: 11px; font-weight: 700; color: {t.accent}; letter-spacing: 0.5px;">RETAIL BROKING CRM</div>'
        f'<div style="font-size: 11px; color: {t.text_muted}; margin-top: 2px;">Dormancy Intelligence</div>'
        f'</div>'
    )

    param_page = st.query_params.get("page")
    if param_page:
        st.session_state["current_nav_page"] = param_page

    if "current_nav_page" not in st.session_state:
        st.session_state["current_nav_page"] = "Overview"

    current_page = st.session_state["current_nav_page"]

    groups = [
        ("MONITOR", [("Overview", None), ("Risk queue", "18k")]),
        ("PLAN", [("Segments and playbook", "5"), ("Experiment planner", None)]),
        ("EVALUATE", [("Model and threshold", "0.693")]),
    ]

    for grp_title, pages in groups:
        st.sidebar.html(
            f'<div style="font-size: 10px; font-weight: 700; color: {t.text_muted}; letter-spacing: 0.8px; padding: 10px 8px 4px 8px;">{grp_title}</div>'
        )
        for page_name, badge in pages:
            is_active = (current_page == page_name)
            badge_str = f"  ({badge})" if badge else ""
            btn_label = f"{page_name}{badge_str}"
            btn_type = "primary" if is_active else "secondary"

            if st.sidebar.button(btn_label, key=f"nav_btn_{page_name}", use_container_width=True, type=btn_type):
                st.session_state["current_nav_page"] = page_name
                st.query_params["page"] = page_name
                st.rerun()

    st.sidebar.html(
        f'<div style="margin-top: 24px; padding: 12px 8px; border-top: 1px solid {t.border}; font-size: 11px; color: {t.text_muted};">'
        f'<div>Target: Day 61-90 Zero Trades</div>'
        f'<div style="margin-top: 4px;">Contact Unit Cost: <strong>₹15.00</strong></div>'
        f'<div style="margin-top: 4px;">Engine Status: <span style="color:{t.positive}; font-weight:600;">● Active</span></div>'
        f'</div>'
    )

    return st.session_state["current_nav_page"]


def render_status_bar(
    rows_shown: int = 20000,
    active_filters: str = "All",
    approved_count: int = 0,
) -> None:
    """Render thin anchored status line at the bottom of the workspace."""
    t = get_current_theme()
    st.html(
        f'<div class="terminal-status-bar" style="display:flex; justify-content:space-between; align-items:center; width:100%; font-size:11px; color:{t.text_muted}; '
        f'background:{t.panel}; border:1px solid {t.border}; border-radius:3px; padding:4px 12px; margin-top:24px;">'
        f'<div class="terminal-status-left" style="display:flex; gap:16px;">'
        f'<span><strong>FILTER:</strong> {active_filters}</span>'
        f'<span><strong>DISPLAYING:</strong> {rows_shown:,} accounts</span>'
        f'<span><strong>APPROVED BATCH:</strong> {approved_count}</span>'
        f'</div>'
        f'<div class="terminal-status-right" style="display:flex; gap:16px; font-family:var(--font-mono);">'
        f'<span>CACHE: 12ms</span>'
        f'<span>HOST: Local:8501</span>'
        f'</div>'
        f'</div>'
    )


# ==============================================================================
# 4. REUSABLE TERMINAL COMPONENTS (KPIs, TAGS, FORMATTERS, CHARTS)
# ==============================================================================

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
    """Render key figures in a rigid, fixed-height ruled strip across the terminal."""
    t = get_current_theme()
    items = []

    for m in metrics:
        label = m.get("label", "")
        value = m.get("value", "")
        sub = m.get("sub", "")
        delta = m.get("delta", None)
        delta_good = m.get("delta_good", True)

        delta_html = ""
        if delta is not None:
            color = t.positive if delta_good else t.negative
            arrow = "▲" if "+" in delta or not delta.startswith("-") else "▼"
            delta_html = f'<span style="color:{color}; font-size:11px; font-weight:600; margin-left:6px;">{delta} {arrow}</span>'

        items.append(
            f'<div class="terminal-metric-item" style="flex:1; min-width:140px; padding:8px 14px; border-right:1px solid {t.border}; display:flex; flex-direction:column; justify-content:center;">'
            f'<div style="font-size:11px; color:{t.text_muted}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:2px;">{label}</div>'
            f'<div style="font-size:20px; font-weight:700; color:{t.text_primary}; line-height:1.2; font-variant-numeric:tabular-nums;">'
            f'{value} {delta_html}'
            f'</div>'
            f'<div style="font-size:11px; color:{t.text_muted}; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{sub}</div>'
            f'</div>'
        )

    if items:
        items[-1] = items[-1].replace(f"border-right:1px solid {t.border};", "border-right:none;")

    strip_html = (
        f'<div class="terminal-metric-strip" style="display:flex; flex-direction:row; flex-wrap:wrap; width:100%; background:{t.panel}; '
        f'border:1px solid {t.border}; border-radius:3px; margin:12px 0 16px 0; min-height:68px;">'
        f'{"".join(items)}'
        f'</div>'
    )
    st.html(strip_html)


def render_section_header(title: str, directive: Optional[str] = None) -> None:
    """Render a clean, plain sentence-case section header with operational directive."""
    t = get_current_theme()
    header_html = f"<div style='margin-bottom: 2px; font-weight: 600; font-size: 16px; color:{t.text_primary};'>{title}</div>"
    if directive:
        header_html += f"<div style='color: {t.text_muted}; font-size: 12px; margin-top: 0; margin-bottom: 12px;'>{directive}</div>"
    st.html(header_html)


def render_callout(text: str, tone: str = "neutral") -> None:
    """Render a clean terminal callout box."""
    t = get_current_theme()
    border_color = t.accent
    if tone == "warning":
        border_color = t.warning
    elif tone == "danger":
        border_color = t.negative
    elif tone == "positive":
        border_color = t.positive

    callout_html = (
        f'<div style="padding:10px 14px; background-color:{t.panel}; border:1px solid {t.border}; '
        f'border-left:3px solid {border_color}; border-radius:3px; margin:10px 0; font-size:12px; color:{t.text_primary}; line-height:1.5;">'
        f'{text}'
        f'</div>'
    )
    st.html(callout_html)


def render_tag(label: str, variant: str = "neutral") -> str:
    """Return inline HTML for semantic status tags."""
    t = get_current_theme()
    bg_color = t.raised
    text_color = t.text_primary
    border_color = t.border

    if variant == "positive":
        bg_color = "rgba(16, 185, 129, 0.15)" if t.name == "dark" else "rgba(5, 150, 105, 0.12)"
        text_color = t.positive
        border_color = t.positive
    elif variant == "negative":
        bg_color = "rgba(239, 68, 68, 0.15)" if t.name == "dark" else "rgba(220, 38, 38, 0.12)"
        text_color = t.negative
        border_color = t.negative
    elif variant == "warning":
        bg_color = "rgba(245, 158, 11, 0.15)" if t.name == "dark" else "rgba(217, 119, 6, 0.12)"
        text_color = t.warning
        border_color = t.warning
    elif variant == "accent":
        bg_color = "rgba(0, 163, 137, 0.15)" if t.name == "dark" else "rgba(14, 90, 107, 0.12)"
        text_color = t.accent
        border_color = t.accent

    return (
        f'<span style="display:inline-block; padding:1px 6px; font-size:10px; font-weight:600; '
        f'background:{bg_color}; color:{text_color}; border:1px solid {border_color}; border-radius:2px; font-family:var(--font-mono);">'
        f'{label}'
        f'</span>'
    )


def render_empty_state(title: str, message: str, command: Optional[str] = None) -> None:
    """Render an informative empty state explaining what to do next."""
    t = get_current_theme()
    cmd_html = f"<div style='margin-top: 12px; font-family: var(--font-mono); background: {t.raised}; border:1px solid {t.border}; padding: 6px 12px; display: inline-block; font-size: 12px; color:{t.accent};'>{command}</div>" if command else ""
    empty_html = (
        f"<div style='background-color: {t.panel}; border: 1px solid {t.border}; border-radius:3px; padding: 32px 20px; text-align: center; margin: 20px 0;'>"
        f"<div style='margin: 0 0 6px 0; font-weight: 600; font-size: 15px; color:{t.text_primary};'>{title}</div>"
        f"<div style='color: {t.text_muted}; font-size: 13px; max-width: 500px; margin: 0 auto;'>{message}</div>"
        f"{cmd_html}"
        f"</div>"
    )
    st.html(empty_html)


def apply_chart_theme(fig: go.Figure, height: int = 320) -> go.Figure:
    """Apply minimal terminal styling rules to Plotly figures.

    Rules:
    - Dark/Light theme aware background and typography.
    - No toolbar, light gridlines, clean margins, IBM Plex Sans font.
    - Fixed right gutter for bar labels so no text is clipped.
    - High contrast text tokens (never white text on light backgrounds).
    """
    t = get_current_theme()

    fig.update_layout(
        font=dict(family="IBM Plex Sans, -apple-system, sans-serif", color=t.text_primary, size=11),
        paper_bgcolor=t.panel,
        plot_bgcolor=t.panel,
        margin=dict(l=12, r=24, t=20, b=24),
        height=height,
        hoverlabel=dict(
            bgcolor=t.raised,
            font_size=11,
            font_family="IBM Plex Sans, -apple-system, sans-serif",
            bordercolor=t.border,
            font_color=t.text_primary,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=t.text_muted),
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=t.gridline,
        gridwidth=1,
        linecolor=t.border,
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=10, color=t.text_muted),
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=t.gridline,
        gridwidth=1,
        linecolor=t.border,
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=10, color=t.text_muted),
    )

    return fig
