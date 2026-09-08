"""
00_Home.py
------------
Landing page — shown before Executive Public Health Overview in the nav.
Just the branded hero graphic, sized to the page width; no additional
header banner on top of it since the image already carries its own
branding/hero content.
"""

from pathlib import Path

import streamlit as st

from src.styling import inject_css
from src.dashboard_report_pipeline import build_dashboard_report_bundle

# Note: st.set_page_config() is intentionally NOT called here — app.py
# already calls it once, centrally, before st.navigation(). See the
# comment in dashboards/2_Laboratory_Healthcare_Capacity.py for why.

inject_css()

st.markdown(
    """
    <style>
    /* Home is an immersive landing surface: remove the shared dashboard
       gutters and let the hero fill the available viewport below the app bar. */
    .block-container {
        max-width: none !important;
        padding: 0 !important;
    }
    [data-testid="stImage"] {
        position: relative;
        width: 100% !important;
        height: calc(100vh - 60px) !important;
        min-height: 420px !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    [data-testid="stImage"] img {
        width: 100% !important;
        height: 100% !important;
        max-height: none !important;
        object-fit: cover !important;
        object-position: center center !important;
    }
    /* Quiet scrim along the base of the hero so the graphic settles into
       the page rather than cutting off on a hard edge. Decorative only —
       no content sits on top of it. */
    [data-testid="stImage"]::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: linear-gradient(
            to bottom,
            rgba(15, 30, 40, 0) 72%,
            rgba(11, 22, 30, 0.28) 100%
        );
    }

    .section-title {
        font-size: 1.28rem;
        font-weight: 700;
        color: #17324D;
        letter-spacing: -0.01em;
        margin-bottom: 4px;
    }
    .section-caption {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 30px;
    }

    /* Dashboard index cards: a quiet, editorial list rather than a
       stacked "SaaS card kit" — a hairline frame, a left accent that
       carries each dashboard's own colour, and one deliberate hover
       response instead of a shared drop shadow on every tile. */
    .home-dashboard-card {
        min-height: 166px;
        box-sizing: border-box;
        background: #FFFFFF;
        border: 1px solid #E4E9EF;
        border-left: 3px solid var(--accent, #0F6B78);
        border-radius: 10px;
        padding: 20px 22px;
        margin-bottom: 20px;
        transition: border-color 0.18s ease, background-color 0.18s ease;
    }
    .home-dashboard-card:hover {
        border-color: var(--accent, #0F6B78);
        background: #FAFCFC;
    }
    .home-dashboard-icon {
        width: 38px;
        height: 38px;
        border-radius: 8px;
        background: var(--accent, #0F6B78);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        flex-shrink: 0;
    }
    .home-dashboard-title {
        font-size: 0.96rem;
        font-weight: 700;
        color: #17324D;
        letter-spacing: -0.01em;
        line-height: 1.3;
    }
    .home-dashboard-desc {
        font-size: 0.85rem;
        color: #51606F;
        line-height: 1.6;
        padding-right: 4px;
    }

    @media (prefers-reduced-motion: reduce) {
        .home-dashboard-card { transition: none; }
    }

    @media (max-width: 760px) {
        .block-container {
            padding: 0 !important;
        }
        [data-testid="stImage"] {
            height: calc(100vh - 60px) !important;
            min-height: 360px !important;
        }
        [data-testid="stImage"] img {
            height: 100% !important;
        }
        .home-dashboard-card {
            min-height: 0;
            padding: 18px 18px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("---")
    st.markdown("## ℹ️ About")
    st.caption(
        "HealthSentinel is a public-health analytics suite for India, "
        "bringing together disease surveillance, environmental risk, lab & "
        "hospital capacity, outbreak monitoring, and health-program "
        "performance in one place."
    )
    st.markdown(
        "**Coverage:** 28 states · Jan 2022 – Dec 2024  \n"
        "**Use case:** Public-health decision support"
    )
    st.markdown("---")
    st.caption("Infosys Public Health Analytics · Internal Use")

_hero_path = Path(__file__).resolve().parent.parent / "assets" / "home_hero.jpg"
st.image(str(_hero_path), width="stretch")

# ==========================================
# Explore the Dashboards — one card per page in the sidebar nav, so the
# landing page tells people what's behind each tab before they click it.
# ==========================================
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Explore the Dashboards</div>'
    '<div class="section-caption">What you\'ll find behind each tab in the sidebar</div>',
    unsafe_allow_html=True,
)

DASHBOARDS = [
    {
        "icon": "📊",
        "title": "Executive Public Health Overview",
        "desc": "National disease burden, outcomes, and state performance summary — the "
                "top-level view for a quick read on how the country is doing.",
        "color": "#0F6B78",
    },
    {
        "icon": "🌍",
        "title": "Geographic & Environmental Intelligence",
        "desc": "Connects geographic risk, environmental stressors (air quality, water "
                "quality, climate) and disease burden to show where attention is most needed.",
        "color": "#16855B",
    },
    {
        "icon": "🧪",
        "title": "Laboratory & Healthcare Capacity",
        "desc": "Testing volumes, positivity rates, vaccination coverage, and hospital / "
                "ICU capacity across states, month by month.",
        "color": "#17324D",
    },
    {
        "icon": "🚨",
        "title": "Outbreak Monitoring & Forecasting",
        "desc": "Live alert levels and containment performance, plus ARIMA-based case "
                "forecasting and a priority containment matrix for active outbreaks.",
        "color": "#C43D3D",
    },
    {
        "icon": "🤝",
        "title": "Health Programs & Population Vulnerability",
        "desc": "Tracks public health program coverage and performance, and flags "
                "vulnerable populations that need attention.",
        "color": "#C98A00",
    },
]

cols = st.columns(2, gap="large")
for i, dash in enumerate(DASHBOARDS):
    with cols[i % 2]:
        st.markdown(
            f"""
            <div class="kpi-card home-dashboard-card" style="--accent:{dash['color']};">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                    <div class="home-dashboard-icon">{dash['icon']}</div>
                    <div class="home-dashboard-title">{dash['title']}</div>
                </div>
                <div class="home-dashboard-desc">{dash['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )