"""
1_Geographic_Environmental_Intelligence.py
-------------------------------------------
Geographic & Environmental Intelligence page.

The page is intentionally kept as Streamlit orchestration. Reusable calculations,
risk logic, and Plotly builders live in src/geographic.py, while the visual system
lives in src/styling.py.
"""

import streamlit as st

from src.data_loader import get_environmental_master, get_surveillance_master
from src.geographic import (
    PLOTLY_CONFIG,
    build_environmental_trend,
    build_gauge,
    build_hotspot_chart,
    build_radar,
    build_state_map,
    build_urban_rural,
    build_water_scatter,
    calculate_kpis,
    calculate_pressure,
    common_layout,
    decision_snapshot,
    filter_data,
    get_date_bounds,
    get_date_window,
    risk_band,
    risk_color,
)
from src.styling import inject_geographic_css, page_header, insight_banner, filter_bar_header
from src.report_generator import add_top_report_button
from src.interactivity import (
    handle_page_enter, stage_filter_updates, clicked_customdata_rows,
    render_click_clear_strip,
)

inject_geographic_css()
# Apply staged chart click-selections / drill-down requests before filter state
# is read (the state widgets are instantiated further down the page).
handle_page_enter()

# Data is filtered by this dashboard's own controls below.
env = get_environmental_master()
ds = get_surveillance_master()
MIN_DATE, MAX_DATE = get_date_bounds(env)


def reset_filters():
    """Reset all dashboard filters to the complete available dataset."""
    st.session_state["geo_period"] = "All available data"
    st.session_state["phs_custom_date_range"] = (MIN_DATE, MAX_DATE)
    st.session_state["geo_region"] = "All Regions"
    st.session_state["geo_state_focus"] = "All States"
    st.session_state["geo_disease_focus"] = "All Diseases"


# Initialize filter state before KPI calculations. The widgets themselves are
# rendered below the KPI cards, but session_state keeps the selected context
# available to the calculations before the widgets are drawn.
st.session_state.setdefault("geo_period", "All available data")
st.session_state.setdefault("phs_custom_date_range", (MIN_DATE, MAX_DATE))
st.session_state.setdefault("geo_region", "All Regions")
st.session_state.setdefault("geo_state_focus", "All States")
st.session_state.setdefault("geo_disease_focus", "All Diseases")

period = st.session_state["geo_period"]
region = st.session_state["geo_region"]
state_focus = st.session_state["geo_state_focus"]
disease_focus = st.session_state["geo_disease_focus"]

region_options = ["All Regions"] + sorted(env["region"].dropna().unique().tolist())
if region not in region_options:
    region = "All Regions"
    st.session_state["geo_region"] = region
state_pool = env if region == "All Regions" else env[env["region"] == region]
state_options = ["All States"] + sorted(state_pool["state_name"].dropna().unique().tolist())
if state_focus not in state_options:
    state_focus = "All States"
    st.session_state["geo_state_focus"] = state_focus
disease_options = ["All Diseases"] + sorted(ds["disease_name"].dropna().unique().tolist())
if disease_focus not in disease_options:
    disease_focus = "All Diseases"
    st.session_state["geo_disease_focus"] = disease_focus

if period == "Custom range":
    custom = st.session_state.get("phs_custom_date_range", (MIN_DATE, MAX_DATE))
    if isinstance(custom, (tuple, list)) and len(custom) == 2:
        start_date, end_date = custom
    else:
        start_date = end_date = custom
else:
    start_date, end_date = get_date_window(period, MIN_DATE, MAX_DATE)


# Header

st.markdown(
    """
    <style>
    .geo-header {
        background: linear-gradient(135deg, #122B45 0%, #17324D 40%, #0F6B78 100%);
        border-radius: 16px;
        padding: 26px 30px;
        margin-bottom: 28px;
        box-shadow: 0 10px 30px rgba(18,43,69,0.20);
        position: relative;
        overflow: hidden;
    }
    .geo-header::before {
        content: "";
        position: absolute;
        top: -60%;
        right: -30%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(72,224,192,0.10) 0%, transparent 60%);
        border-radius: 50%;
    }
    .geo-header::after {
        content: "";
        position: absolute;
        bottom: -50%;
        left: 20%;
        width: 250px;
        height: 250px;
        background: radial-gradient(circle, rgba(105,169,255,0.08) 0%, transparent 60%);
        border-radius: 50%;
    }
    .geo-header-content {
        position: relative;
        z-index: 1;
    }
    .geo-header-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: white;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .geo-header-sub {
        font-size: 0.95rem;
        color: rgba(255,255,255,0.78);
        margin: 0;
        line-height: 1.5;
        max-width: 750px;
    }
    .geo-header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 14px;
        background: rgba(255,255,255,0.12);
        backdrop-filter: blur(4px);
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 700;
        color: rgba(255,255,255,0.9);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        border: 1px solid rgba(255,255,255,0.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="geo-header">
        <div class="geo-header-content">
            <h1 class="geo-header-title">Geographic & Environmental Intelligence</h1>
            <p class="geo-header-sub">A decision-support view that connects geographic risk, environmental stressors and disease burden to identify where public-health attention is most needed.</p>
            <div class="geo-header-badge">🌍 Decision Support · Multi-factor Risk</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Filtered data

env_f, ds_f = filter_data(
    env, ds, start_date, end_date, region, state_focus, disease_focus
)

if env_f.empty:
    st.error(
        "No environmental records match the selected filters. "
        "Broaden the analysis period or geography."
    )
    st.stop()

# The report generator's chart builders expect the shorter column names
# used elsewhere in the app (e.g. "geographic_risk" rather than
# "geographic_risk_score"), so pass a renamed copy for report purposes only
# — the page's own charts keep using env_f/ds_f untouched.
_report_df = env_f.rename(columns={
    "geographic_risk_score": "geographic_risk",
    "environmental_risk_score": "environmental_risk",
    "water_quality_index": "water_quality",
    "sanitation_coverage_pct": "sanitation",
    "healthcare_accessibility_score": "healthcare_access",
})
add_top_report_button(
    "Geographic & Environmental Intelligence",
    _report_df,
    {
        "Analysis Period": period if period != "Custom range"
            else f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}",
        "Region": region,
        "State": state_focus,
        "Disease Focus": disease_focus,
    },
)


# KPI row

kpis = calculate_kpis(env_f)

insight_banner(
    f"Environmental risk is averaging **{kpis['environmental_risk']:.1f}** ({risk_band(kpis['environmental_risk'])}); "
    f"AQI is standing at **{kpis['aqi']:.0f}**; water quality index is **{kpis['water_quality']:.1f}/100** "
    f"({region if region != 'All Regions' else 'across all regions'})."
)

kpi_items = [
    ("Geographic Risk", f'{kpis["geographic_risk"]:.1f}', "risk score",
     "linear-gradient(135deg, #D5F5E3 0%, #FCF3CF 50%, #FADBD8 100%)"),
    ("Environmental Risk", f'{kpis["environmental_risk"]:.1f}', risk_band(kpis["environmental_risk"]), "#F5B7B1"),
    ("AQI", f'{kpis["aqi"]:.0f}', "average index", "#FDEBD0"),
    ("Rainfall", f'{kpis["rainfall"]:.1f} mm', "average", "#D6EAF8"),
    ("Temperature", f'{kpis["temperature"]:.1f} °C', "average", "#FADBD8"),
    ("Water Quality", f'{kpis["water_quality"]:.1f}', "index / 100", "#EBF5FB"),
    ("Sanitation", f'{kpis["sanitation"]:.1f}%', "coverage", "#D5F5E3"),
    ("Healthcare Access", f'{kpis["healthcare_access"]:.1f}', "score / 100", "#E8F8F5"),
]
cards = ['<div class="kpi-grid">']
for label, value, meta, bg in kpi_items:
    cards.append(
        f'<div class="kpi" style="background:{bg};"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-meta">● {meta}</div></div>'
    )
cards.append("</div>")
st.markdown("".join(cards), unsafe_allow_html=True)

# Main-page filter bar — intentionally placed directly under the KPI cards.
with st.container(border=True):
    header_col, reset_col = st.columns([5, 1])
    with header_col:
        filter_bar_header("Selections are applied to every visual on this page")
    with reset_col:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        st.button("♻️ Reset", use_container_width=True, key="geo_reset_filters", on_click=reset_filters)

    row1 = st.columns([1.3, 1, 1, 1], gap="medium")
    with row1[0]:
        st.selectbox(
            "Analysis period",
            ["All available data", "Latest month", "Past 30 days", "Past 90 days", "Past 12 months", "Custom range"],
            key="geo_period",
            help=(f"Your dataset ends on {MAX_DATE.strftime('%d %b %Y')}. Relative periods are calculated from the latest available data."),
        )
    with row1[1]:
        st.selectbox("Region", region_options, key="geo_region")
    with row1[2]:
        st.selectbox("State focus", state_options, key="geo_state_focus")
    with row1[3]:
        st.selectbox("Disease for case analysis", disease_options, key="geo_disease_focus")

    if period == "Custom range":
        st.date_input(
            "Custom date range",
            value=(MIN_DATE, MAX_DATE),
            min_value=MIN_DATE,
            max_value=MAX_DATE,
            key="phs_custom_date_range",
        )

    active_geo = []
    for label, value, default in [
        ("Period", period, "All available data"),
        ("Region", region, "All Regions"),
        ("State", state_focus, "All States"),
        ("Disease", disease_focus, "All Diseases"),
    ]:
        if value != default:
            active_geo.append(f'<span class="active-filter-chip">{label}: {value}</span>')
    if period == "Custom range":
        active_geo.append('<span class="active-filter-chip">Custom date range selected</span>')
    if not active_geo:
        active_geo.append('<span class="active-filter-chip">All available data</span>')
    st.markdown(
        '<div class="active-filter-summary"><span class="summary-label">Active filters:</span>' + "".join(active_geo) + '</div>',
        unsafe_allow_html=True,
    )

# Visible one-click way back from a chart click-selection (state focus).
_geo_state_now = st.session_state.get("geo_state_focus", "All States")
render_click_clear_strip([
    {"label": "State", "key": "geo_state_focus",
     "current": None if _geo_state_now in ("All States", "All") else _geo_state_now,
     "clear": {"geo_state_focus": "All States"}},
])

st.markdown(
    f"<div class='filter-bar-caption' style='margin:10px 4px 0;'>Data window: <b>{start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}</b> · Environmental risk = environmental fact table · Disease burden = disease surveillance fact table.</div>",
    unsafe_allow_html=True,
)


# Geographic risk landscape

state_map, fig_geo = build_state_map(env_f, ds_f)

# Embed the state name + exact metrics into every bubble so a click on the
# map can drive the page filters and the hover shows precise numbers.
_geo_cd = state_map[[
    "state_name", "region", "geographic_risk", "environmental_risk",
    "aqi", "water_quality", "case_rate", "hotspots",
]].fillna(0).copy()
fig_geo.update_traces(customdata=_geo_cd.values.tolist())
fig_geo.update_traces(
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>Region: %{customdata[1]}"
        "<br>Geographic Risk: %{customdata[2]:.1f}<br>Environmental Risk: %{customdata[3]:.1f}"
        "<br>AQI: %{customdata[4]:.0f}<br>Water Quality: %{customdata[5]:.1f}/100"
        "<br>Case Rate /100k: %{customdata[6]:.1f}<br>Hotspot observations: %{customdata[7]:.0f}"
        "<br><i>👆 click to filter this page to the state</i><extra></extra>"
    )
)

st.markdown(
    '<div class="section-title">Geographic Risk Landscape</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-caption">Interactive state-risk pulse map • bubble size = geographic risk • '
    'color = risk intensity • hover for full state intelligence • 💡 click a bubble to filter the page</div>',
    unsafe_allow_html=True,
)
_ev_geo = st.plotly_chart(fig_geo, use_container_width=True, config=PLOTLY_CONFIG,
                           on_select="rerun", selection_mode=["points"])
_rows_geo = clicked_customdata_rows(_ev_geo)
if _rows_geo:
    stage_filter_updates({"geo_state_focus": _rows_geo[0][0]}, origin_label="State")

# Hotspots + environmental fingerprint + gauge

c1, c2, c3 = st.columns([1.35, 1.05, .85])

with c1:
    st.markdown('<div class="section-title">Geographic Hotspots</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Top states ranked by geographic risk · 💡 click a bar to filter the page</div>', unsafe_allow_html=True)
    fig_hot = build_hotspot_chart(state_map)
    _hot_names = [str(v) for v in fig_hot.data[0].y]
    fig_hot.update_traces(
        customdata=[[s] for s in _hot_names],
        hovertemplate="%{y}<br>Geographic Risk: <b>%{x:.1f}</b><br><i>👆 click to filter to this state</i><extra></extra>",
    )
    _ev_hot = st.plotly_chart(fig_hot, use_container_width=True, config=PLOTLY_CONFIG,
                              on_select="rerun", selection_mode=["points"])
    _rows_hot = clicked_customdata_rows(_ev_hot)
    if _rows_hot:
        stage_filter_updates({"geo_state_focus": _rows_hot[0][0]}, origin_label="State")
    with st.expander("Show details — top states by geographic risk", expanded=False):
        st.dataframe(
            state_map.nlargest(10, "geographic_risk")[
                ["state_name", "region", "geographic_risk", "environmental_risk", "aqi", "hotspots"]
            ].rename(columns={
                "state_name": "State", "geographic_risk": "Geographic Risk",
                "environmental_risk": "Environmental Risk", "hotspots": "Hotspot obs",
            }),
            use_container_width=True, height=250, hide_index=True,
        )

with c2:
    st.markdown('<div class="section-title">Environmental Risk Fingerprint</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Which environmental pressures are driving attention?</div>', unsafe_allow_html=True)
    st.plotly_chart(
        build_radar(calculate_pressure(env_f)),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

with c3:
    st.markdown('<div class="section-title">Risk Gauge</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Composite environmental risk</div>', unsafe_allow_html=True)
    st.plotly_chart(
        build_gauge(kpis["environmental_risk"]),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

# Urban/rural disease burden + environmental trend

c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-title">Urban vs Rural Disease Burden</div>', unsafe_allow_html=True)
    caption = (
        "Reported cases by settlement type"
        if disease_focus == "All Diseases"
        else f"Reported cases by settlement type • {disease_focus}"
    )
    st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)
    if ds_f.empty:
        st.info("No disease surveillance records match the selected filters.")
    else:
        st.plotly_chart(build_urban_rural(ds_f), use_container_width=True, config=PLOTLY_CONFIG)

with c2:
    st.markdown('<div class="section-title">Environmental Indicators Trend</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Use the selector to switch the environmental signal</div>', unsafe_allow_html=True)
    trend_metric = st.selectbox(
        "Indicator",
        ["AQI", "Rainfall", "Temperature", "Water Quality", "Environmental Risk"],
        key="trend_indicator",
        label_visibility="collapsed",
    )
    st.plotly_chart(
        build_environmental_trend(env_f, trend_metric),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )


# Water quality vs zoonotic incidence

st.markdown('<div class="section-title">Water Quality vs Zoonotic Incidence</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Bubble size = case rate • color = environmental risk • each bubble is a state • 💡 click a bubble to filter the page</div>',
    unsafe_allow_html=True,
)

fig_sc, scatter, corr = build_water_scatter(env_f)
if fig_sc is not None:
    _scatter_rows = [[s] for s in scatter["state_name"].astype(str).tolist()]
    fig_sc.update_traces(customdata=_scatter_rows)
    fig_sc.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Water Quality: %{x:.1f}<br>Zoonotic Incidence: %{y:.1f}"
            "<br><i>👆 click to filter to this state</i><extra></extra>"
        )
    )
    _ev_sc = st.plotly_chart(fig_sc, use_container_width=True, config=PLOTLY_CONFIG,
                             on_select="rerun", selection_mode=["points"])
    _rows_sc = clicked_customdata_rows(_ev_sc)
    if _rows_sc:
        stage_filter_updates({"geo_state_focus": _rows_sc[0][0]}, origin_label="State")

    strength = "weak" if abs(corr) < .3 else "moderate" if abs(corr) < .6 else "strong"
    direction = "positive" if corr >= 0 else "negative"
    st.markdown(
        f'<div class="insight"><b>Analyst signal:</b> water quality and zoonotic incidence show a '
        f'<b>{strength} {direction}</b> association in the selected data (r = {corr:.2f}). '
        f'This is an analytical association, not proof of causation.</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Show details — state-level water quality vs zoonotic incidence", expanded=False):
        st.dataframe(
            scatter.rename(columns={
                "state_name": "State", "water_quality": "Water Quality",
                "zoonotic_incidence": "Zoonotic Incidence", "case_rate": "Case Rate /100k",
                "environmental_risk": "Environmental Risk", "sanitation": "Sanitation (%)",
            }),
            use_container_width=True, height=260, hide_index=True,
        )
else:
    st.info("Not enough state-level records to calculate the water-quality association.")

# Decision snapshot

st.markdown('<div class="section-title">Decision Snapshot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Three signals a public-health decision maker should notice first</div>',
    unsafe_allow_html=True,
)

top_state, aqi_state, water_state = decision_snapshot(state_map)
d1, d2, d3 = st.columns(3)

with d1:
    st.markdown(
        f'<div class="small-card"><div class="small-card-title">Highest geographic risk</div>'
        f'<div class="small-card-value">{top_state["state_name"]} • {top_state["geographic_risk"]:.1f}</div></div>',
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        f'<div class="small-card"><div class="small-card-title">Highest AQI</div>'
        f'<div class="small-card-value">{aqi_state["state_name"]} • {aqi_state["aqi"]:.0f}</div></div>',
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        f'<div class="small-card"><div class="small-card-title">Lowest water quality</div>'
        f'<div class="small-card-value">{water_state["state_name"]} • {water_state["water_quality"]:.1f}</div></div>',
        unsafe_allow_html=True,
    )

