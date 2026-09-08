"""
styling.py
----------
Shared CSS and small reusable UI components (KPI tiles, section headers)
so every page of the dashboard renders with a consistent, corporate look
and feel.
"""

import streamlit as st

from src.chart_colors import (
    HEATMAP_SCALE,
    HOTSPOT_SCALE,
    PIE_SEQUENCE,
    PIE_SEVERITY,
    BAR_SEQUENCE,
    STATUS_SUCCESS,
    STATUS_WARNING,
    STATUS_DANGER,
)

# --------------------------------------------------------------------------- #
# Brand palette
# --------------------------------------------------------------------------- #
PRIMARY = "#17324D"    # Deep Navy — sidebar, headings, key branding
ACCENT = "#0F6B78"     # Teal Blue — active states, buttons, highlights, key chart data
# Slightly darker than the previous #F0F4F8 so white cards/panels read as
# clearly separated from the page instead of nearly blending into it.
NEUTRAL_BG = "#E8EEF3"  # Soft cool gray — page background
CARD_BG = "#FFFFFF"    # White — KPI cards, tables, panels, charts
TEXT = "#1A1A2E"       # Deep charcoal — headings & primary information (softer than pure black)
MUTED = "#5A6378"      # Slate gray — labels & supporting information (was pure black, too harsh)
SUCCESS = STATUS_SUCCESS    # Green
WARNING = STATUS_WARNING    # Amber
DANGER = STATUS_DANGER      # Red
# Extra accent colors for richer visual hierarchy
AMBER_GLOW = "#F59E0B"
GREEN_BRIGHT = "#10B981"
RED_BRIGHT = "#EF4444"
PURPLE_ACCENT = "#8B5CF6"
SLATE_DARK = "#334155"

# --------------------------------------------------------------------------- #
# Chart color system — imported from src/chart_colors.py (the single source
# of truth) and re-exported here since most dashboard pages already import
# their palette from src.styling. See chart_colors.py for the full rationale.
#   RISK_HEATMAP_SCALE -> heatmaps / matrices (Green -> Yellow -> Red)
#   HOTSPOT_SCALE       -> choropleths / geo maps / ranking bars (cool -> warm)
#   PIE_SEQUENCE        -> pie & donut charts (soft pastels)
#   PIE_SEVERITY        -> High/Moderate/Low severity pies (pastel, matches heatmap)
#   BAR_SEQUENCE        -> plain categorical bar charts (executive blue/gray/teal)
# --------------------------------------------------------------------------- #
RISK_HEATMAP_SCALE = HEATMAP_SCALE
HOTSPOT_SCALE = HOTSPOT_SCALE
PIE_SEQUENCE = PIE_SEQUENCE
PIE_SEVERITY = PIE_SEVERITY
BAR_SEQUENCE = BAR_SEQUENCE

CUSTOM_CSS = f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Crisper text rendering across browsers — helps with the soft/fuzzy
       text some Windows + Chromium combinations show on semi-transparent
       or backdrop-filtered elements. */
    html, body {{
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
    }}

    .stApp {{
        background-color: {NEUTRAL_BG};
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }}

    /* Breathing room between stacked elements (rows, charts, tables) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
        margin-bottom: 26px;
    }}
    div[data-testid="stPlotlyChart"] {{
        margin-bottom: 6px;
    }}
    div[data-testid="stDataFrame"] {{
        margin-bottom: 6px;
        border-radius: 10px !important;
        overflow: hidden;
    }}

    /* Consistent gutters between cards in the same row */
    div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div {{
        padding-right: 10px;
    }}
    div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div:last-child {{
        padding-right: 0;
    }}

    /* ================================
       DROPDOWNS / POPOVERS — always render on top
       BaseWeb portals the open dropdown list to the document body, outside
       the sidebar/card it visually belongs to. Streamlit's own layout and
       Plotly's chart canvases both create their own stacking contexts, so
       without an explicit z-index here an open dropdown can appear on top
       visually but still sit BELOW a chart for click purposes — a click
       meant for a dropdown option lands on whatever chart/button is
       underneath instead. This single rule fixes that for every page.
       ================================ */
    div[data-baseweb="popover"] {{
        z-index: 999999 !important;
    }}

    .dash-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px 24px;
        background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 60%, #16855B 100%);
        border-radius: 14px;
        color: white;
        margin-bottom: 28px;
        box-shadow: 0 6px 18px rgba(23,50,77,0.14);
    }}
    .dash-header h1 {{
        font-size: 1.7rem;
        margin: 0;
        font-weight: 800;
        color: white;
        letter-spacing: -0.02em;
    }}
    .dash-header p {{
        margin: 4px 0 0 0;
        font-size: 0.88rem;
        color: rgba(255,255,255,0.82);
        line-height: 1.4;
    }}
    /* Badge: previously used backdrop-filter: blur(4px), which on several
       Chromium/Windows combinations blurs the badge's OWN text along with
       whatever sits behind it. A solid, slightly lighter fill gives the
       same "frosted chip" look without ever risking blurred text. */
    .dash-badge {{
        background: rgba(255,255,255,0.22);
        border: 1px solid rgba(255,255,255,0.28);
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}

    /* KPI tiles: a hairline frame plus each metric's own accent colour on
       the left edge, rather than a stacked pair of drop shadows on every
       tile. One quiet shadow for lift, a slightly stronger one only on
       hover so the surface still responds to the pointer. */
    .kpi-card {{
        background: {CARD_BG};
        border: 1px solid #E2E8F0;
        border-left: 4px solid {ACCENT};
        border-radius: 12px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 1px 4px rgba(23, 50, 77, 0.06);
        height: 100%;
        min-width: 0;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: box-shadow 0.18s ease, border-color 0.18s ease;
        /* Keeps this card's own stacking context self-contained so its
           hover/shadow transition can never interfere with the click
           target of a widget layered nearby. */
        isolation: isolate;
    }}
    .kpi-card:hover {{
        box-shadow: 0 4px 14px rgba(23, 50, 77, 0.10);
        border-color: #CBD8E2;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .kpi-card {{ transition: none; }}
    }}
    .kpi-label {{
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: {MUTED};
        font-weight: 750;
        margin-bottom: 6px;
        white-space: normal;
        overflow: visible;
        text-overflow: unset;
        word-wrap: break-word;
        line-height: 1.25;
        min-height: 2.3em;
    }}
    .kpi-value {{
        font-size: clamp(1.12rem, 1.75vw, 1.65rem);
        font-weight: 700;
        color: {TEXT};
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-sub {{
        font-size: 0.72rem;
        color: {MUTED};
        margin-top: 3px;
    }}

    .section-title {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {TEXT};
        margin: 18px 0 4px 0;
        border-left: 4px solid {ACCENT};
        padding-left: 12px;
        letter-spacing: -0.01em;
        line-height: 1.3;
    }}
    .section-caption {{
        font-size: 0.92rem;
        color: #475569;
        padding-left: 16px;
        margin-bottom: 14px;
        line-height: 1.5;
        font-weight: 450;
    }}

    /* Decision Snapshot cards — used by snapshot_row() on every dashboard
       page so the 3-signal callout renders as a consistent light card
       with a teal accent bar — fits the clean light theme where dark
       navy/teal is reserved for the sidebar and header only. */
    .small-card {{
        border: 1px solid #E2E8F0;
        border-left: 4px solid {ACCENT};
        background: #FFFFFF;
        border-radius: 12px;
        padding: 16px 18px;
        height: 100%;
        box-shadow: 0 1px 4px rgba(15,23,42,0.06);
    }}
    .small-card-title {{
        color: {ACCENT};
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .small-card-value {{
        color: {TEXT};
        font-size: 1.3rem;
        font-weight: 800;
        margin-top: 7px;
    }}

    /* ================================
       CARD-STYLE WRAPPER for every bordered container (st.container(border=True))
       Previously declared TWICE in this file — once as a bare
       background+radius rule, then again further down re-declaring border,
       radius, background and shadow with !important. Two rules targeting
       the exact same selector is exactly the kind of thing that causes
       "sometimes it looks right, sometimes it doesn't": whichever wins
       depends on the rest of the cascade for a given page's extra CSS
       (e.g. GEOGRAPHIC_CSS layered on top). Consolidated into one rule.
       ================================ */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {CARD_BG} !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 4px rgba(23,50,77,0.04) !important;
    }}

    /* ================================
       GLOBAL CAPTION / SMALL-TEXT OVERRIDE
       st.caption() and similar helper text render very light grey by
       default, which is hard to read against the light page background.
       Force it to solid black everywhere in the main content area (the
       sidebar has its own white-on-navy override further down).
       ================================ */
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] *,
    .stCaption,
    .stCaption * {{
        color: {TEXT} !important;
        opacity: 1 !important;
        -webkit-text-fill-color: {TEXT} !important;
    }}

    /* ================================
       MAIN-PAGE WIDGET CONTRAST (belt-and-suspenders)
       Every selectbox / multiselect / date-input / number-input that
       lives OUTSIDE the sidebar (i.e. everywhere filters now live, plus
       the Upload & Custom Analysis pickers) must render dark, readable
       text on a light fill regardless of the active theme config —
       this does not touch anything inside section[data-testid="stSidebar"].
       ================================ */
    div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border-color: #CBD5E1 !important;
    }}
    div[data-baseweb="select"] * {{
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
        opacity: 1 !important;
        font-size: 0.95rem !important;
    }}
    /* Widget labels ("State" / "Year" / "Month") above the main-page
       filter selects — Streamlit gives these no explicit size by default,
       so bump them up to match the larger filter-bar text below. */
    div[data-testid="stVerticalBlockBorderWrapper"] label p,
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"] p {{
        font-size: 0.95rem !important;
        font-weight: 650 !important;
        color: {TEXT} !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: {TEXT} !important;
    }}

    /* Selected multiselect values: high-contrast teal chips with white text.
       The old global select rule forced chip text to black, which made the
       selected filters difficult to read on the dark teal chip background. */
    div[data-baseweb="select"] [data-baseweb="tag"] {{
        background-color: {ACCENT} !important;
        border: 1px solid {ACCENT} !important;
        border-radius: 6px !important;
    }}
    div[data-baseweb="select"] [data-baseweb="tag"] *,
    div[data-baseweb="select"] [data-baseweb="tag"] span {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    div[data-baseweb="select"] [data-baseweb="tag"] svg {{
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }}
    div[data-baseweb="popover"] li {{
        color: {TEXT} !important;
        background-color: #FFFFFF !important;
    }}
    div[data-baseweb="popover"] li:hover {{
        background-color: #EEF3F6 !important;
    }}
    /* The currently-selected row inside an open dropdown list. Setting
       BOTH color and -webkit-text-fill-color together (never just one)
       is what keeps this from being silently overridden by a later
       wildcard rule on some browsers — see the sidebar dropdown fix
       further down for the bug this pattern prevents. */
    div[data-baseweb="popover"] li[aria-selected="true"] {{
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
        background-color: #E6F0F1 !important;
        font-weight: 700 !important;
    }}
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input {{
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
        background-color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: rgba(255,255,255,0.08) !important;
        border-color: rgba(255,255,255,0.25) !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
        color: #F8FBFF !important;
        -webkit-text-fill-color: #F8FBFF !important;
    }}

    /* ================================
       MAIN-PAGE FILTER BAR
       Card-style container that holds each dashboard's filters at the
       top of the main content area (replacing sidebar filter panels).
       ================================ */
    .active-filter-summary {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 7px;
        margin-top: 12px;
        padding: 10px 14px;
        background: #EFF6F7;
        border: 1px solid #CFE1E4;
        border-radius: 10px;
        font-size: 0.92rem;
        color: {PRIMARY};
    }}
    .active-filter-summary .summary-label {{
        font-weight: 800;
        margin-right: 2px;
    }}
    .active-filter-chip {{
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        background: {ACCENT};
        color: #FFFFFF !important;
        font-weight: 700;
        line-height: 1.1;
        font-size: 0.82rem;
    }}

    .filter-bar-title {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 1.15rem;
        color: {TEXT};
        margin-bottom: 2px;
    }}
    .filter-bar-caption {{
        font-size: 0.9rem;
        color: {MUTED};
        margin-bottom: 10px;
    }}

    section[data-testid="stSidebar"] {{
        background-color: {PRIMARY};
    }}

    /* Sidebar logo (HealthSentinel name + icon, set via st.logo()) —
       Streamlit renders this quite small by default; size it up so the
       brand reads clearly at the top of the nav. */
    [data-testid="stSidebar"] [data-testid="stLogo"] {{
        height: 3.2rem !important;
        max-height: none !important;
        width: auto !important;
        margin: 14px 0 10px 18px !important;
    }}
    [data-testid="stSidebarCollapsedControl"] [data-testid="stLogo"] {{
        height: 2.4rem !important;
    }}

    section[data-testid="stSidebar"] * {{
        color: #E8EDF1 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stCaption * {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown strong {{
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown h2 {{
        font-size: 1rem;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.25);
    }}
    section[data-testid="stSidebar"] button {{
        background-color: {ACCENT} !important;
        color: white !important;
        border: none !important;
    }}

    /* ================================
       SIDEBAR NAVIGATION — page links with icons, hover, and active state
       ================================ */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
        padding-top: 6px;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {{
        gap: 2px;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
    section[data-testid="stSidebar"] nav a {{
        display: flex;
        align-items: center;
        gap: 10px;
        border-radius: 8px;
        margin: 2px 8px;
        padding: 10px 14px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #D7E2EA !important;
        background: transparent !important;
        border-left: 3px solid transparent !important;
        transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a::before,
    section[data-testid="stSidebar"] nav a::before {{
        content: "";
        width: 18px;
        height: 18px;
        flex-shrink: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
        line-height: 1;
        opacity: 0.85;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(1) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(1) a::before {{ content: "🏠"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(2) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(2) a::before {{ content: "📊"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(3) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(3) a::before {{ content: "🌍"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(4) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(4) a::before {{ content: "🧪"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(5) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(5) a::before {{ content: "🚨"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(6) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(6) a::before {{ content: "🤝"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(7) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(7) a::before {{ content: "📤"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:nth-child(8) a::before,
    section[data-testid="stSidebar"] nav li:nth-child(8) a::before {{ content: "💬"; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
    section[data-testid="stSidebar"] nav a:hover {{
        background: rgba(255,255,255,0.10) !important;
        border-left-color: rgba(255,255,255,0.35) !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover::before,
    section[data-testid="stSidebar"] nav a:hover::before {{
        opacity: 1;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
    section[data-testid="stSidebar"] nav a[aria-current="page"] {{
        background: {ACCENT} !important;
        border-left-color: #FFFFFF !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(15,107,120,0.40);
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]::before,
    section[data-testid="stSidebar"] nav a[aria-current="page"]::before {{
        opacity: 1;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span,
    section[data-testid="stSidebar"] nav a[aria-current="page"] span {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{
        margin: 10px 8px !important;
        border-color: rgba(255,255,255,0.14) !important;
    }}

    /* ================================
       NATIVE st.metric() KPI CARDS
       (used on pages that need delta/MoM indicators, e.g. Executive
       Overview, Laboratory & Healthcare Capacity)
       ================================ */
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG} !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: 0 1px 3px rgba(23, 50, 77, 0.06) !important;
        min-height: 105px !important;
        box-sizing: border-box !important;
    }}
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] div,
    [data-testid="stMetricLabel"] span {{
        color: {TEXT} !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: {TEXT} !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        white-space: normal !important;
        word-break: break-word !important;
        line-height: 1.2 !important;
    }}
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    [data-testid="stMetricValue"] div,
    [data-testid="stMetricValue"] span {{
        color: {PRIMARY} !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: {PRIMARY} !important;
        font-size: 25px !important;
        font-weight: 700 !important;
    }}
    div[data-testid="stMetric"] p {{
        opacity: 1 !important;
        color: {TEXT} !important;
    }}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, badge: str = "LIVE"):
    st.markdown(
        f"""
        <div class="dash-header" style="
            background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 60%, #16855B 100%);
            box-shadow: 0 6px 18px rgba(23,50,77,0.16);
        ">
            <div style="position:relative; z-index:1;">
                <h1 style="font-size:1.7rem; font-weight:800; color:white; margin:0 0 6px 0; letter-spacing:-0.02em;">{title}</h1>
                <p style="font-size:0.85rem; color:rgba(255,255,255,0.82); margin:0; line-height:1.45;">{subtitle}</p>
            </div>
            <div class="dash-badge" style="
                background: rgba(255,255,255,0.22);
                border: 1px solid rgba(255,255,255,0.28);
            ">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", color: str = PRIMARY, bg: str = None):
    bg_style = f"background:{bg};" if bg else ""
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{color};{bg_style}">
            <div class="kpi-label" style="margin-bottom:8px;">{label}</div>
            <div class="kpi-value" style="font-size:clamp(1.2rem, 2vw, 1.7rem); font-weight:800; line-height:1.1;">{value}</div>
            <div class="kpi-sub" style="margin-top:5px;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def snapshot_row(items: list, title: str = "Decision Snapshot",
                  caption: str = "Three signals a decision maker should notice first"):
    """Render the 3-card 'Decision Snapshot' row (matches the pattern used
    on Geographic & Environmental Intelligence) on any page. `items` is a
    list of exactly 3 (label, value) tuples.

    Uses the .small-card / .section-title / .section-caption classes from
    the shared stylesheet (originally added for the Geographic page's dark
    high-contrast cards) — works fine over the plain light page background
    used elsewhere since it's a self-contained dark card, not a full-page
    theme change.
    """
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)

    cols = st.columns(3, gap="medium")
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="small-card"><div class="small-card-title">{label}</div>'
                f'<div class="small-card-value">{value}</div></div>',
                unsafe_allow_html=True,
            )


def kpi_card_delta(label: str, value: str, delta: str = None, color: str = PRIMARY,
                    bg: str = None, invert: bool = False, badge: str = None, badge_color: str = None,
                    sub: str = ""):
    """Like kpi_card(), but renders a small colored MoM delta line underneath
    the value (e.g. "▲ +3.6% MoM" in green, "▼ -4.1% MoM" in red) — used on
    pages migrated from native st.metric() that need per-card background
    colors, which st.metric() can't do.

    invert=True flips which direction counts as "good" (e.g. a rising
    positivity rate is bad, so its delta should read red even though it's
    an increase).

    sub (optional) renders the exact figure in the small muted sub line
    (mirrors kpi_card's sub= behaviour) so compacted values never hide
    the true number.
    """
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    delta_html = ""
    if delta:
        is_up = delta.strip().startswith("+")
        good = is_up if not invert else not is_up
        delta_color = SUCCESS if good else DANGER
        arrow = "▲" if is_up else "▼"
        delta_bg = "rgba(22,133,91,0.10)" if good else "rgba(196,61,61,0.10)"
        delta_html = (
            f'<div style="display:inline-flex; align-items:center; gap:5px; '
            f'background:{delta_bg}; padding:3px 10px; border-radius:999px; '
            f'margin-top:6px; font-size:0.72rem; font-weight:700; color:{delta_color};">'
            f'<span style="font-size:0.65rem;">{arrow}</span>'
            f'{delta.lstrip("+-")}</div>'
        )

    badge_html = ""
    if badge:
        bc = badge_color or color
        # Solid text on a light tint background, plus a matching border,
        # rather than text colored the same as its own near-white tinted
        # background alone — keeps low-contrast hues (amber especially)
        # from washing out.
        badge_html = (
            f'<span style="background:{bc}1A; color:{bc}; padding:2px 8px; border-radius:6px; '
            f'font-size:0.66rem; font-weight:700; border:1px solid {bc}66; margin-left:auto;">{badge}</span>'
        )

    bg_style = f"background:{bg};" if bg else ""
    # Built as one unbroken line (no internal newlines) rather than an
    # indented multi-line f-string: when badge_html/delta_html are empty,
    # a multi-line version leaves a blank/whitespace-only line, which
    # terminates Streamlit's markdown HTML-block parsing early and causes
    # everything after it to render as a literal code block instead of HTML.
    html = (
        f'<div class="kpi-card" style="border-left-color:{color};{bg_style}">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<div class="kpi-label" style="margin-bottom:0;">{label}</div>'
        f'{badge_html}'
        f'</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{sub_html}'
        f'{delta_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def filter_bar_header(caption: str = "Applies across all visuals on this page", title: str = "Filters"):
    """Small header row (icon + title + caption) placed at the top of a
    main-page filter container. Call this first inside
    `with st.container(border=True):`, then lay out the actual filter
    widgets in st.columns() beneath it.
    """
    st.markdown(
        '<div class="filter-bar-title" style="display:flex; align-items:center; gap:8px; font-weight:800; font-size:1.05rem; color:#17324D; margin-bottom:2px;">🔎 ' + title + '</div>'
        '<div class="filter-bar-caption" style="font-size:0.82rem; color:#475569; margin-bottom:10px; line-height:1.35;">' + caption + '</div>',
        unsafe_allow_html=True,
    )


def section_title(title: str, caption: str = ""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


def insight_banner(text: str, icon: str = "📌"):
    """The single-line 'key point' callout shown directly under the page
    header on every dashboard (e.g. "📌 Positivity rate is down 2.5% MoM;
    ICU utilization is MODERATE at 63.8%."). `text` may include simple
    **bold** markdown-style markers, which are converted to <b> tags.

    Styled as a highlighted callout (amber-tinted background + left
    accent bar) so the key takeaway visually stands out from the rest
    of the page instead of blending in as a plain card.
    """
    import re
    html_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    st.markdown(
        f"""
        <div style="
            background: #FFF6E0;
            border-left: 5px solid {WARNING};
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 22px;
            font-size: 15px;
            font-weight: 600;
            color: {TEXT};
            box-shadow: 0 1px 4px rgba(18, 53, 91, 0.06);
        ">
            <span style="margin-right:8px;">{icon}</span>
            {html_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def coming_soon(dashboard_name: str, description: str, planned_visuals: list[str]):
    """Reserved layout for a dashboard that hasn't been built out yet.

    Keeps the page on-brand (header + card) and previews what will land
    here, so the nav item isn't just a dead end during the presentation.
    """
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{ACCENT}; padding:28px 28px 24px 28px;">
            <div style="font-size:0.72rem; font-weight:700; letter-spacing:0.5px;
                        color:{ACCENT}; text-transform:uppercase; margin-bottom:8px;">
                🚧 In Development
            </div>
            <div style="font-size:1.1rem; font-weight:700; color:{TEXT}; margin-bottom:6px;">
                {dashboard_name}
            </div>
            <div style="font-size:0.88rem; color:{MUTED}; max-width:640px; line-height:1.5;">
                {description}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    section_title("Planned Visuals", "Scoped for the next build pass")
    cols = st.columns(2, gap="large")
    for i, item in enumerate(planned_visuals):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="background:{CARD_BG}; border:1px dashed #C7D2DA; border-radius:8px;
                            padding:14px 16px; margin-bottom:14px; font-size:0.85rem; color:{TEXT};">
                    <b>{i + 1}.</b> {item}
                </div>
                """,
                unsafe_allow_html=True,
            )


GEOGRAPHIC_CSS = """<style>
.dash-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: linear-gradient(90deg, #17324D 0%, #0F6B78 100%);
    border-radius: 10px;
    color: white;
    margin-bottom: 26px;
}
.dash-header h1 {
    font-size: 1.7rem;
    margin: 0;
    font-weight: 700;
    color: white;
}
.dash-header p {
    margin: 2px 0 0 0;
    font-size: 0.82rem;
    color: #FFFFFF;
}
.dash-badge {
    background: rgba(255,255,255,0.15);
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

:root {
    --bg: #E8EEF3;
    --panel: #FFFFFF;
    --panel2: #17324D;
    --line: #D9E1E8;
    --text: #000000;
    --muted: #000000;
    --teal: #0F6B78;
    --blue: #0F6B78;
    --amber: #C98A00;
    --orange: #C98A00;
    --red: #C43D3D;
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                 "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% -5%, rgba(72,224,192,.10), transparent 24%),
        radial-gradient(circle at 95% 5%, rgba(105,169,255,.08), transparent 22%),
        var(--bg);
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #122B45 0%, #173A59 100%) !important;
    border-right: none !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 0 16px 18px !important;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] .stMarkdown {
    margin-bottom: 0 !important;
}

[data-testid="stSidebar"] h2 {
    font-size: 1.05rem !important;
    font-weight: 800 !important;
    letter-spacing: -.02em !important;
    margin: 6px 0 2px !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: rgba(255,255,255,.72) !important;
    font-size: .74rem !important;
    line-height: 1.55 !important;
}

[data-testid="stSidebar"] hr {
    margin: 18px 0 20px !important;
    border-color: rgba(255,255,255,.12) !important;
}

[data-testid="stSidebar"] label {
    color: #F7FBFF !important;
    font-size: .72rem !important;
    font-weight: 650 !important;
    letter-spacing: .01em !important;
}

[data-testid="stSidebar"] .stSelectbox {
    margin-bottom: 13px !important;
}

[data-testid="stSidebar"] .stSelectbox > div > div {
    border-radius: 10px !important;
}

/* Keep sidebar labels white, but make selected filter values readable. */
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(255,255,255,.08) !important;
    border: 1px solid rgba(255,255,255,.16) !important;
    border-radius: 10px !important;
    min-height: 42px !important;
    box-shadow: none !important;
}
/* Force the CURRENT selected value (the closed control showing the
   chosen option) to be visible inside every sidebar selectbox.
   Streamlit/BaseWeb can render the value as a nested div rather than a
   data-baseweb="select-value" element, so target the complete value tree. */
[data-testid="stSidebar"] div[data-baseweb="select"] [role="button"],
[data-testid="stSidebar"] div[data-baseweb="select"] [role="button"] > div,
[data-testid="stSidebar"] div[data-baseweb="select"] [role="button"] div,
[data-testid="stSidebar"] div[data-baseweb="select"] [role="button"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] input,
[data-testid="stSidebar"] div[data-baseweb="select"] [class*="singleValue"],
[data-testid="stSidebar"] div[data-baseweb="select"] [class*="placeholder"] {
    color: #F8FBFF !important;
    -webkit-text-fill-color: #F8FBFF !important;
    opacity: 1 !important;
}
/* BUG FIX: the open dropdown list is portaled OUTSIDE this sidebar
   selector's DOM subtree, so this "make it black on white" rule for the
   highlighted option never actually matched it — and the wildcard rule
   just below (which forces white text on every descendant) was the only
   thing that ever applied to the highlighted row, painting it white
   text on a white row background: invisible. Fixed at the source below
   with div[data-baseweb="popover"] li[aria-selected="true"] instead,
   which correctly reaches the portaled list. This selector is left as a
   harmless no-op guard rather than removed, in case a future BaseWeb
   version nests the list differently.
*/
[data-testid="stSidebar"] div[data-baseweb="select"] [aria-selected="true"] {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    background: #FFFFFF !important;
}
/* Exclude aria-selected items from the "everything white" sweep so a fix
   applied elsewhere (or above) can never be silently overridden again. */
[data-testid="stSidebar"] div[data-baseweb="select"] *:not([aria-selected="true"]) {
    -webkit-text-fill-color: #F8FBFF !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] svg {
    fill: #000000 !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}
/* Dropdown menu — the actual portaled list. Selected row gets its own
   readable combination so "currently chosen" is visibly distinct from
   the rest of the list without ever being white-on-white. */
div[data-baseweb="popover"] li {
    color: #000000 !important;
    background: #FFFFFF !important;
}
div[data-baseweb="popover"] li:hover {
    background: #F5F7FA !important;
}
div[data-baseweb="popover"] li[aria-selected="true"] {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    background: #E6F0F1 !important;
    font-weight: 700 !important;
}

[data-testid="stAppViewContainer"] > .main {
    width: 100% !important;
}

[data-testid="stAppViewContainer"] > .main > div {
    width: 100% !important;
}

[data-testid="stAppViewContainer"] .block-container {
    width: 100% !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-top: 1.45rem;
    padding-bottom: 1.5rem;
}

 .hero {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
    margin: 0 0 18px 0;
    padding: 22px 30px;
    min-height: 120px;
    box-sizing: border-box;
    border-radius: 13px;
    background: linear-gradient(105deg, #223752 0%, #286879 100%);
    box-shadow: 0 6px 16px rgba(20,48,72,.14);
}

.hero-left {
    min-width: 0;
}

.eyebrow {
    display: none;
}

.hero-title {
    margin: 0;
    color: #ffffff;
    font-size: 1.5rem;
    line-height: 1.15;
    letter-spacing: -.01em;
    font-weight: 800;
}

.hero-subtitle {
    color: rgba(255,255,255,.82);
    margin-top: 10px;
    font-size: .88rem;
    line-height: 1.35;
    max-width: 850px;
}

.hero-badge {
    flex: 0 0 auto;
    border: 0;
    background: rgba(255,255,255,.16);
    color: #ffffff;
    padding: 7px 11px;
    border-radius: 999px;
    font-size: .62rem;
    font-weight: 800;
    letter-spacing: .03em;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 0 0 22px;
}

.kpi {
    height: 136px !important;
    padding: 18px 18px 15px !important;
    border-radius: 15px !important;
    border: 1px solid #DCE3EA !important;
    border-left: 4px solid #17324D !important;
    background: #FFFFFF;
    box-shadow: 0 1px 4px rgba(23,50,77,.08) !important;
    transition: box-shadow 0.18s ease !important;
    isolation: isolate;
}
.kpi:hover {
    box-shadow: 0 5px 16px rgba(23,50,77,.12) !important;
}
@media (prefers-reduced-motion: reduce) {
    .kpi { transition: none !important; }
}

.kpi:nth-child(2) { border-left-color: #17324D !important; }
.kpi:nth-child(3) { border-left-color: #D89B00 !important; }
.kpi:nth-child(4) { border-left-color: #2B8B70 !important; }
.kpi:nth-child(5) { border-left-color: #C84343 !important; }
.kpi:nth-child(6) { border-left-color: #2B8B70 !important; }
.kpi:nth-child(7) { border-left-color: #2B8B70 !important; }

.kpi-label {
    color: #000000 !important;
    font-size: .76rem !important;
    line-height: 1.2 !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: .075em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kpi-value {
    color: #172A40 !important;
    font-size: 1.65rem !important;
    line-height: 1 !important;
    font-weight: 850 !important;
    white-space: nowrap;
}

.kpi-meta {
    color: #000000 !important;
    font-size: .66rem !important;
    font-weight: 500 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.section-title {
    margin: 18px 0 3px;
    color: #000000;
    font-size: 1.25rem;
    font-weight: 850;
    letter-spacing: -.01em;
}

.section-caption {
    color: #000000;
    font-size: .95rem;
    margin-bottom: 8px;
}

.panel {
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    background: #FFFFFF;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(15,23,42,0.04);
}

.insight {
    border: 1px solid rgba(15,107,120,.20);
    border-left: 4px solid #0F6B78;
    background: #F0F9FA;
    border-radius: 10px;
    padding: 14px 18px;
    color: #0F172A !important;
    font-size: .88rem;
    font-weight: 500;
    line-height: 1.5;
}

.small-card {
    border: 1px solid #E2E8F0;
    border-left: 4px solid #0F6B78;
    background: #FFFFFF;
    border-radius: 12px;
    padding: 16px 18px;
    height: 100%;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06);
}

.small-card-title {
    color: #0F6B78;
    font-size: .74rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .06em;
}

.small-card-value {
    color: #0F172A;
    font-size: 1.3rem;
    font-weight: 800;
    margin-top: 7px;
}

.footer {
    text-align: center;
    color: #000000;
    font-size: .68rem;
    padding: 18px 0 4px;
}

@media (max-width: 1250px) {
    .kpi-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
    .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .hero { align-items: flex-start; flex-direction: column; min-height: auto; padding: 24px; }
}

div[data-testid="stPlotlyChart"] {
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    overflow: hidden;
    background: #FFFFFF;
    box-shadow: 0 1px 4px rgba(15,23,42,0.04);
}

    /* Supplied light professional theme */
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] input {
        background: rgba(255,255,255,.08) !important;
        color: #FFFFFF !important;
        border-color: rgba(255,255,255,.16) !important;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption { color: #FFFFFF !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.14); }

    /* =========================================================
   RESET FILTER BUTTON
   ========================================================= */

[data-testid="stSidebar"] .reset-filter-btn button {
    width: 100% !important;
    min-height: 40px !important;
    border-radius: 9px !important;
    border: 1px solid rgba(255,255,255,.20) !important;
    background: rgba(255,255,255,.08) !important;
    color: #FFFFFF !important;
    font-size: .78rem !important;
    font-weight: 700 !important;
    transition: all .2s ease !important;
}

[data-testid="stSidebar"] .reset-filter-btn button:hover {
    background: rgba(255,255,255,.16) !important;
    border-color: rgba(255,255,255,.32) !important;
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] .reset-filter-btn button:active {
    transform: scale(.98);
}

</style>"""


def inject_geographic_css():
    """Inject the visual system used by the Geographic & Environmental page.

    Loads the shared CUSTOM_CSS first (so this page gets the same hidden
    menu/footer, sidebar nav highlighting, and readable-caption rules as
    every other dashboard) and then layers the page's own GEOGRAPHIC_CSS
    on top for its distinct dark decision-support styling.
    """
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(GEOGRAPHIC_CSS, unsafe_allow_html=True)