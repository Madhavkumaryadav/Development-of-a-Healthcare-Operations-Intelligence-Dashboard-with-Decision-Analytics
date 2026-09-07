"""
0_Executive_Public_Health_Overview.py
---------------------------------------
Executive Public Health Overview — landing page of the multipage Streamlit
application. Two tabs:
  - Executive Summary: leadership-facing KPIs + six standard visuals
    summarizing disease burden, distribution, and state-level performance.
  - Disease Surveillance: disease-wise trends, state heatmap, outbreak
    alerts, testing/positivity performance and source-of-report reliability.

Both tabs share one sidebar filter panel and one filtered dataset, so
selections stay in sync between them.

Run with:  streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import (
    get_surveillance_master, get_outbreak_master, get_lab_master, apply_common_filters,
)
from src.filters import get_current_filters, render_filter_bar
from src.kpis import compute_kpis, compute_hosp_icu_rates, format_number
from src.report_generator import add_top_report_button
from src.interactivity import (
    drill_button, handle_page_enter, stage_filter_updates, clicked_customdata_rows,
    render_click_clear_strip, pct_delta, latest_two_rows, mom_delta_text,
)
from src.styling import (
    inject_css, page_header, kpi_card, kpi_card_delta, section_title, snapshot_row,
    insight_banner, PRIMARY, ACCENT, DANGER, SUCCESS, WARNING, RISK_HEATMAP_SCALE,
    HOTSPOT_SCALE, PIE_SEQUENCE,
)

# Soft pastel sequence for pie/donut charts — same palette used for every
# other pie in the suite so slice colors don't shift meaning page to page.
BRAND_SEQUENCE = PIE_SEQUENCE
# 12 visually distinct colors so every disease gets its own hue (no repeats/clumsiness)
TREND_PALETTE = [
    "#17324D", "#0F6B78", "#C43D3D", "#C98A00", "#3B8E93", "#8E44AD",
    "#2E7D32", "#1F4A63", "#E07A5F", "#5B7DB1", "#A0522D", "#7BB4B0",
]
# "Top diseases by burden" is a hotspot-style ranking (higher burden = more
# concerning), so it uses the same cool -> warm HOTSPOT_SCALE as every other
# hotspot chart/map in the suite instead of a plain navy/teal gradient.
NAVY_TEAL_SCALE = HOTSPOT_SCALE

inject_css()
# Honours drill-down requests from KPI cards and applies chart click-selections
# that were staged after the filter widgets were drawn on the previous run.
handle_page_enter()

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .exec-header {
        background: linear-gradient(135deg, #17324D 0%, #0F6B78 50%, #16855B 100%);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(23,50,77,0.15);
        position: relative;
        overflow: hidden;
    }
    .exec-header::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
        border-radius: 50%;
    }
    .exec-header::after {
        content: "";
        position: absolute;
        bottom: -40%;
        left: -10%;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 70%);
        border-radius: 50%;
    }
    .exec-header-content {
        position: relative;
        z-index: 1;
    }
    .exec-header-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: white;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .exec-header-sub {
        font-size: 0.95rem;
        color: rgba(255,255,255,0.82);
        margin: 0;
        line-height: 1.45;
        max-width: 720px;
    }
    .exec-header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(4px);
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        color: white;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border: 1px solid rgba(255,255,255,0.20);
        margin-top: 12px;
    }
    .exec-header-badge-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.85); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="exec-header">
        <div class="exec-header-content">
            <h1 class="exec-header-title">Executive Public Health Overview</h1>
            <p class="exec-header-sub">National disease burden, outcomes, and state performance summary</p>
            <div class="exec-header-badge">
                <span class="exec-header-badge-dot"></span>
                LIVE DATA · Jan 2022 – Dec 2024
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

master = get_surveillance_master()


# --------------------------------------------------------------------------- #
# Month-over-Month delta strings for the KPI cards (compare the latest month
# present in the filtered data to the previous month under the same filters).
# --------------------------------------------------------------------------- #
def _exec_mom(df):
    """Return {metric: "+x% MoM"/"-x% MoM"} deltas for the top KPI row."""
    cur, prev = latest_two_rows(df)
    if cur is None or prev is None:
        return {}

    def _s(frame, col):
        return float(frame[col].sum()) if frame is not None and not frame.empty and col in frame.columns else 0.0

    def _pop(frame):
        if frame is None or frame.empty:
            return None
        f = frame
        if {"state_id", "date_id"}.issubset(frame.columns):
            f = frame.drop_duplicates(subset=["state_id", "date_id"])
        return float(f["population_under_surveillance"].sum())

    d = {}
    for key, col in [
        ("total", "total_reported_cases"), ("active", "active_cases"),
        ("recovered", "recovered_cases"), ("deaths", "deaths"),
    ]:
        d[key] = mom_delta_text(cur, prev, col, "sum", "pct")
    d["risk"] = mom_delta_text(cur, prev, "public_health_risk_score", "mean", "pp", suffix="MoM", decimals=2)

    pop_cur, pop_prev = _pop(cur), _pop(prev)
    d["pop"] = pct_delta(pop_cur, pop_prev) if pop_cur is not None and pop_prev is not None else None

    # Derived rates (CFR / Recovery) recomputed from the summed month columns.
    prev_total = _s(prev, "total_reported_cases")
    if prev_total > 0:
        def _rate(frame):
            t = _s(frame, "total_reported_cases")
            return (_s(frame, "deaths") / t * 100) if t else 0.0, (_s(frame, "recovered_cases") / t * 100) if t else 0.0
        cfr_c, rec_c = _rate(cur)
        cfr_p, rec_p = _rate(prev)
        d["cfr"] = f"{cfr_c - cfr_p:+.2f}% MoM"
        d["recovery"] = f"{rec_c - rec_p:+.2f}% MoM"
    return d


# Month label for a single (year, month_name) click-filter chip.
def _period_display():
    years = list(st.session_state.get("f_year", []) or [])
    months = list(st.session_state.get("f_month", []) or [])
    if len(years) == 1 and len(months) == 1:
        return [f"{months[0]} {years[0]}"]
    return months + years


# --------------------------------------------------------------------------- #
# Filters + data (shared across both tabs)
# --------------------------------------------------------------------------- #
filters = get_current_filters()
df = apply_common_filters(
    master,
    states=filters["states"],
    regions=filters["regions"],
    years=filters["years"],
    months=filters["months"],
    diseases=filters["diseases"],
    disease_categories=filters["disease_categories"],
    sources=filters["sources"],
)

if df.empty:
    st.warning("No records match the current filter selection. Please broaden your filters.")
    st.stop()

add_top_report_button(
    "Executive Public Health Overview",
    df,
    {
        "Region": filters["regions"],
        "State": filters["states"],
        "Year": filters["years"],
        "Month": filters["months"],
        "Disease Type": filters["disease_categories"],
        "Disease": filters["diseases"],
        "Primary Source": filters["sources"],
    },
)

kpis = compute_kpis(df)
rates = compute_hosp_icu_rates(df)

_scope_states = filters["states"] if filters.get("states") else None
_scope_text = f"{len(_scope_states)} selected state(s)" if _scope_states else "all states"
insight_banner(
    f"Case fatality rate is **{kpis['case_fatality_rate']}%**; recovery rate is standing at "
    f"**{kpis['recovery_rate']}%**; hospitalization rate is **{rates['hospitalization_rate']}%** "
    f"({_scope_text})."
)

tab_summary, tab_surveillance = st.tabs(["📊 Executive Summary", "🦠 Disease Surveillance"])

# =============================================================================== #
# TAB 1 — Executive Summary
# =============================================================================== #
with tab_summary:
    # ----------------------------------------------------------------------- #
    # KPI Row — custom kpi_card() with light pastel backgrounds per card
    # (4 + 4 layout)
    # ----------------------------------------------------------------------- #
    risk = kpis["public_health_risk_score"]
    mom = _exec_mom(df)

    r1 = st.columns(4, gap="medium")
    with r1[0]:
        kpi_card_delta("Population Under Surveillance", format_number(kpis["population_under_surveillance"]),
                       delta=mom.get("pop"), bg="#D6EAF8")
        drill_button("geographic", None, key="drill_exec_pop", label="↗ Geographic & Environmental")
    with r1[1]:
        kpi_card_delta("Total Reported Cases", format_number(kpis["total_reported_cases"]),
                       delta=mom.get("total"), bg="#EBF5FB")
        drill_button("geographic", None, key="drill_exec_total", label="↗ Geographic & Environmental")
    with r1[2]:
        kpi_card_delta("Active Cases", format_number(kpis["active_cases"]),
                       delta=mom.get("active"), invert=True, bg="#FDEBD0")
        drill_button("outbreak", {"status_filter": "Active"}, key="drill_exec_active", label="↗ Outbreak Monitoring")
    with r1[3]:
        kpi_card_delta("Recovered Cases", format_number(kpis["recovered_cases"]),
                       delta=mom.get("recovered"), bg="#D5F5E3")
        drill_button("outbreak", None, key="drill_exec_recovered", label="↗ Outbreak Monitoring")

    r2 = st.columns(4, gap="medium")
    with r2[0]:
        kpi_card_delta("Deaths (Monthly)", format_number(kpis["deaths"]),
                       delta=mom.get("deaths"), invert=True, bg="#FADBD8")
        drill_button("outbreak", None, key="drill_exec_deaths", label="↗ Outbreak Monitoring")
    with r2[1]:
        kpi_card_delta("Case Fatality Rate", f'{kpis["case_fatality_rate"]}%',
                       delta=mom.get("cfr"), invert=True, bg="#F5B7B1")
        drill_button("outbreak", None, key="drill_exec_cfr", label="↗ Outbreak Monitoring")
    with r2[2]:
        kpi_card_delta("Recovery Rate", f'{kpis["recovery_rate"]}%',
                       delta=mom.get("recovery"), bg="#E8F8F5")
        drill_button("outbreak", None, key="drill_exec_rec_rate", label="↗ Outbreak Monitoring")
    with r2[3]:
        kpi_card_delta(
            "Public Health Risk Score", f"{risk}", delta=mom.get("risk"), invert=True,
            bg="linear-gradient(135deg, #D5F5E3 0%, #FCF3CF 50%, #FADBD8 100%)",
        )
        drill_button("programs", None, key="drill_exec_risk", label="↗ Health Programs & Vulnerability")

    # Shared filters intentionally sit directly below the KPI cards so the
    # decision-maker sees the metric context first and the active selections
    # immediately underneath. The state is read before rendering, so every
    # KPI/chart already reflects the selected values on each rerun.
    filters = render_filter_bar()

    # Visible one-click way back from any chart click-selection.
    render_click_clear_strip([
        {"label": "State", "key": "f_state", "current": list(st.session_state.get("f_state", []) or []),
         "clear": {"f_state": []}},
        {"label": "Disease", "key": "f_disease", "current": list(st.session_state.get("f_disease", []) or []),
         "clear": {"f_disease": []}},
        {"label": "Disease type", "key": "f_disease_cat", "current": list(st.session_state.get("f_disease_cat", []) or []),
         "clear": {"f_disease_cat": []}},
        {"label": "Period", "key": "f_year", "current": _period_display(),
         "clear": {"f_year": [], "f_month": []}},
    ])

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------------- #
    # Row 1 — Visual 1 (Trend) & Visual 3 (Donut)
    # ----------------------------------------------------------------------- #
    c1, c2 = st.columns([2, 1], gap="large")

    with c1:
        section_title("Monthly Disease Trend", "Total reported cases over time · 💡 click a point to filter the page to that month")
        trend = (
            df.groupby(["year", "month_num", "month_name"], as_index=False)["total_reported_cases"]
            .sum()
            .sort_values(["year", "month_num"])
        )
        trend["period"] = trend["month_name"].str[:3] + " " + trend["year"].astype(str)
        fig1 = px.line(
            trend, x="period", y="total_reported_cases", markers=True,
            color_discrete_sequence=[ACCENT],
        )
        fig1.update_traces(
            line_width=3, fill="tozeroy", fillcolor="rgba(15,107,120,0.10)",
            customdata=trend[["year", "month_name"]].astype(str).values.tolist(),
            hovertemplate=(
                "%{x}<br><b>%{y:,.0f}</b> reported cases"
                "<br><i>👆 click to filter to this month</i><extra></extra>"
            ),
        )
        fig1.update_layout(
            height=340, margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=None, yaxis_title="Total Reported Cases",
            plot_bgcolor="white", paper_bgcolor="white",
        )
        _ev1 = st.plotly_chart(fig1, use_container_width=True, on_select="rerun", selection_mode=["points"])
        _rows1 = clicked_customdata_rows(_ev1)
        if _rows1:
            stage_filter_updates({"f_year": [_rows1[0][0]], "f_month": [_rows1[0][1]]}, origin_label="Period")

    with c2:
        section_title("Disease Distribution", "Share of reported cases by category")
        dist = df.groupby("disease_category", as_index=False)["total_reported_cases"].sum()
        fig3 = px.pie(
            dist, names="disease_category", values="total_reported_cases", hole=0.55,
            color_discrete_sequence=BRAND_SEQUENCE,
        )
        fig3.update_traces(
            textinfo="percent+label", textposition="outside",
            textfont=dict(color="#000000", size=12),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} cases (%{percent:.1%})<extra></extra>",
        )
        fig3.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # ----------------------------------------------------------------------- #
    # Row 2 — Visual 2 (Clustered column) & Visual 4 (Hosp/ICU)
    # ----------------------------------------------------------------------- #
    c3, c4 = st.columns(2, gap="large")

    with c3:
        section_title("Active vs Recovered vs Deaths", "Monthly outcome comparison · 💡 click a bar to filter to that month")
        outcome = (
            df.groupby(["year", "month_num", "month_name"], as_index=False)
            .agg(active_cases=("active_cases", "sum"),
                 recovered_cases=("recovered_cases", "sum"),
                 deaths=("deaths", "sum"))
            .sort_values(["year", "month_num"])
        )
        outcome["period"] = outcome["month_name"].str[:3] + " " + outcome["year"].astype(str)
        _period_rows = outcome[["year", "month_name"]].astype(str).values.tolist()
        fig2 = go.Figure()
        fig2.add_bar(name="Active Cases", x=outcome["period"], y=outcome["active_cases"], marker_color=WARNING,
                     customdata=_period_rows,
                     hovertemplate="%{x}<br>Active: <b>%{y:,.0f}</b><br><i>👆 click to filter</i><extra></extra>")
        fig2.add_bar(name="Recovered Cases", x=outcome["period"], y=outcome["recovered_cases"], marker_color=SUCCESS,
                     customdata=_period_rows,
                     hovertemplate="%{x}<br>Recovered: <b>%{y:,.0f}</b><br><i>👆 click to filter</i><extra></extra>")
        fig2.add_bar(name="Deaths", x=outcome["period"], y=outcome["deaths"], marker_color=DANGER,
                     customdata=_period_rows,
                     hovertemplate="%{x}<br>Deaths: <b>%{y:,.0f}</b><br><i>👆 click to filter</i><extra></extra>")
        fig2.update_layout(
            barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        _ev2 = st.plotly_chart(fig2, use_container_width=True, on_select="rerun", selection_mode=["points"])
        _rows2 = clicked_customdata_rows(_ev2)
        if _rows2:
            stage_filter_updates({"f_year": [_rows2[0][0]], "f_month": [_rows2[0][1]]}, origin_label="Period")

    with c4:
        section_title("Hospitalization & ICU Admission Rate", "% of reported cases · 💡 click a state bar to filter the whole page")
        hosp_by_state = (
            df.groupby("state_name", as_index=False)
            .agg(
                hospitalized_cases=("hospitalized_cases", "sum"),
                icu_admissions=("icu_admissions", "sum"),
                total_reported_cases=("total_reported_cases", "sum"),
            )
        )
        hosp_by_state["Hospitalization Rate"] = (
            hosp_by_state["hospitalized_cases"] / hosp_by_state["total_reported_cases"] * 100
        ).fillna(0)
        hosp_by_state["ICU Admission Rate"] = (
            hosp_by_state["icu_admissions"] / hosp_by_state["total_reported_cases"] * 100
        ).fillna(0)
        hosp_by_state = hosp_by_state.sort_values("Hospitalization Rate", ascending=False).head(10)
        _state_rows = [[s] for s in hosp_by_state["state_name"].astype(str).tolist()]
        fig4 = go.Figure()
        fig4.add_bar(name="Hospitalization Rate", x=hosp_by_state["state_name"], y=hosp_by_state["Hospitalization Rate"],
                     marker_color=PRIMARY, customdata=_state_rows,
                     hovertemplate="%{x}<br>Hospitalization: <b>%{y:.1f}%</b><br><i>👆 click to filter</i><extra></extra>")
        fig4.add_bar(name="ICU Admission Rate", x=hosp_by_state["state_name"], y=hosp_by_state["ICU Admission Rate"],
                     marker_color=DANGER, customdata=_state_rows,
                     hovertemplate="%{x}<br>ICU Admission: <b>%{y:.1f}%</b><br><i>👆 click to filter</i><extra></extra>")
        fig4.update_layout(
            barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            xaxis_tickangle=-35,
        )
        _ev4 = st.plotly_chart(fig4, use_container_width=True, on_select="rerun", selection_mode=["points"])
        _rows4 = clicked_customdata_rows(_ev4)
        if _rows4:
            stage_filter_updates({"f_state": [_rows4[0][0]]}, origin_label="State")

    # ----------------------------------------------------------------------- #
    # Row 3 — Visual 5 (Scatter) & Visual 6 (State ranking table)
    # ----------------------------------------------------------------------- #
    c5, c6 = st.columns([1, 2], gap="large")

    with c5:
        section_title("Recovery vs Mortality Rate", "By state (bubble size = total cases) · 💡 click a bubble to filter the page to that state")
        scatter_df = (
            df.groupby("state_name", as_index=False)
            .agg(total_reported_cases=("total_reported_cases", "sum"),
                 deaths=("deaths", "sum"),
                 recovered_cases=("recovered_cases", "sum"))
        )
        scatter_df["Recovery Rate"] = (scatter_df["recovered_cases"] / scatter_df["total_reported_cases"] * 100).fillna(0)
        scatter_df["Mortality Rate"] = (scatter_df["deaths"] / scatter_df["total_reported_cases"] * 100).fillna(0)
        # Recovery rate cannot meaningfully exceed 100% — a handful of low-volume
        # states show >100% due to cross-period reporting noise, and left unclipped
        # they stretch the x-axis so far that every other state collapses into one
        # unreadable cluster. Cap display at 100% and keep the true value in hover.
        scatter_df["Recovery Rate (raw)"] = scatter_df["Recovery Rate"]
        scatter_df["Recovery Rate"] = scatter_df["Recovery Rate"].clip(upper=100)
        scatter_df["total_cases_label"] = scatter_df["total_reported_cases"].apply(lambda v: f"{v:,.0f}")

        fig5 = px.scatter(
            scatter_df, x="Recovery Rate", y="Mortality Rate", size="total_reported_cases",
            color="Mortality Rate", color_continuous_scale=HOTSPOT_SCALE, hover_name="state_name",
            size_max=34, opacity=0.75,
            custom_data=["state_name", "total_cases_label", "Recovery Rate (raw)"],
        )
        fig5.update_traces(
            marker=dict(line=dict(width=1, color="white")),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Recovery Rate: %{customdata[2]:.1f}%"
                "<br>Mortality Rate: %{y:.2f}%<br>Total Cases: %{customdata[1]}"
                "<br><i>👆 click to filter to this state</i><extra></extra>"
            ),
        )
        fig5.update_layout(
            height=380, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(title="Recovery Rate (%)", range=[60, 102], showgrid=True, gridcolor="#EEF2F5"),
            yaxis=dict(title="Mortality Rate (%)", showgrid=True, gridcolor="#EEF2F5"),
            coloraxis_colorbar=dict(title="Mortality"),
        )
        _ev5 = st.plotly_chart(fig5, use_container_width=True, on_select="rerun", selection_mode=["points"])
        _rows5 = clicked_customdata_rows(_ev5)
        if _rows5:
            stage_filter_updates({"f_state": [_rows5[0][0]]}, origin_label="State")
        st.caption("Recovery rate capped at 100% for readability; a few low-volume states report >100% due to cross-period data noise.")

    with c6:
        section_title("State Ranking", "Sorted by total reported cases · conditional formatting on CFR & Recovery Rate")
        rank = (
            df.groupby("state_name", as_index=False)
            .agg(
                Cases=("total_reported_cases", "sum"),
                Active=("active_cases", "sum"),
                Deaths=("deaths", "sum"),
                Recovered=("recovered_cases", "sum"),
            )
        )
        rank["Recovery Rate"] = (rank["Recovered"] / rank["Cases"] * 100).round(2).fillna(0)
        rank["CFR"] = (rank["Deaths"] / rank["Cases"] * 100).round(2).fillna(0)
        rank = rank.drop(columns=["Recovered"]).sort_values("Cases", ascending=False).reset_index(drop=True)
        rank.index += 1
        rank = rank.rename(columns={"state_name": "State"})

        styled = (
            rank.style
            .background_gradient(subset=["Cases"], cmap="Blues")
            .background_gradient(subset=["CFR"], cmap="Reds")
            .background_gradient(subset=["Recovery Rate"], cmap="Greens")
            .format({"Cases": "{:,.0f}", "Active": "{:,.0f}", "Deaths": "{:,.0f}",
                      "Recovery Rate": "{:.2f}%", "CFR": "{:.2f}%"})
        )
        st.dataframe(styled, use_container_width=True, height=380)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    top_cases = rank.sort_values("Cases", ascending=False).iloc[0]
    top_cfr = rank.sort_values("CFR", ascending=False).iloc[0]
    # Recovery Rate is not capped in `rank` (unlike the scatter chart above,
    # which explicitly clips it) — a handful of low-volume states report
    # >100% due to the same cross-period data noise noted under that chart.
    # Exclude those here too, so the snapshot doesn't headline a data
    # artifact as if it were a real result.
    plausible_recovery = rank[rank["Recovery Rate"] <= 100]
    top_recovery = (plausible_recovery if not plausible_recovery.empty else rank).sort_values(
        "Recovery Rate", ascending=False
    ).iloc[0]
    snapshot_row([
        ("Highest case burden", f'{top_cases["State"]} • {top_cases["Cases"]:,.0f}'),
        ("Highest case fatality rate", f'{top_cfr["State"]} • {top_cfr["CFR"]:.2f}%'),
        ("Highest recovery rate", f'{top_recovery["State"]} • {top_recovery["Recovery Rate"]:.2f}%'),
    ])

    # ----------------------------------------------------------------------- #
    # Compare mode — pick 2+ states and view them side-by-side (Task 4)
    # ----------------------------------------------------------------------- #
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        compare_on = st.checkbox(
            "⚖️ Compare mode — see 2+ states side-by-side",
            key="exec_compare_on",
            help="Switches on a side-by-side state comparison below. Every other chart on this page "
                 "still respects your page filters; the comparison panel ignores the State filter so "
                 "multiple states can be compared at once.",
        )
        if compare_on:
            # Same filters as the page, except the State filter is dropped so
            # several states can be compared at the same time.
            compare_pool = apply_common_filters(
                master,
                states=None,
                regions=filters["regions"], years=filters["years"], months=filters["months"],
                diseases=filters["diseases"], disease_categories=filters["disease_categories"],
                sources=filters["sources"],
            )
            _burden = (
                compare_pool.groupby("state_name", as_index=False)["total_reported_cases"]
                .sum().sort_values("total_reported_cases", ascending=False)
            )
            _state_opts = _burden["state_name"].tolist()
            _defaults = [s for s in _state_opts[:3] if s]
            picked_compare = st.multiselect(
                "States to compare (2–5 recommended)", options=_state_opts, default=_defaults,
                key="exec_compare_states",
            )
            if len(picked_compare) >= 2:
                comp = compare_pool[compare_pool["state_name"].isin(picked_compare)]
                comp_trend = (
                    comp.groupby(["year", "month_num", "month_name", "state_name"], as_index=False)
                    ["total_reported_cases"].sum().sort_values(["year", "month_num"])
                )
                comp_trend["period"] = comp_trend["month_name"].str[:3] + " " + comp_trend["year"].astype(str)
                fig_cmp = px.line(
                    comp_trend, x="period", y="total_reported_cases", color="state_name", markers=True,
                    color_discrete_sequence=TREND_PALETTE,
                )
                fig_cmp.update_traces(line_width=2.5, marker=dict(size=5))
                fig_cmp.update_layout(
                    height=330, margin=dict(l=10, r=10, t=20, b=10),
                    xaxis_title=None, yaxis_title="Total Reported Cases",
                    plot_bgcolor="white", paper_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                st.plotly_chart(fig_cmp, use_container_width=True)

                _cmp_kpis = []
                for _state in picked_compare:
                    _sub = compare_pool[compare_pool["state_name"] == _state]
                    if _sub.empty:
                        continue
                    _k = compute_kpis(_sub)
                    _cmp_kpis.append(
                        (_state, format_number(_k["total_reported_cases"]),
                         f"{_k['case_fatality_rate']}%", f"{_k['recovery_rate']}%")
                    )
                if _cmp_kpis:
                    cmp_header = st.columns([2, 1.2, 1.2, 1.2], gap="medium")
                    for col, txt in zip(cmp_header, ["<b>State</b>", "<b>Total Cases</b>", "<b>CFR</b>", "<b>Recovery</b>"]):
                        with col:
                            st.markdown(txt, unsafe_allow_html=True)
                    for _row in _cmp_kpis:
                        cmp_cols = st.columns([2, 1.2, 1.2, 1.2], gap="medium")
                        for col, val in zip(cmp_cols, _row):
                            with col:
                                st.markdown(f"<div style='padding:6px 2px;font-size:0.95rem;'>{val}</div>",
                                            unsafe_allow_html=True)
                st.caption("Comparison ignores the State filter above, but keeps region/year/month/disease filters and the sidebar Global scope.")
            else:
                st.info("Pick at least two states to see them side-by-side.")

    # ----------------------------------------------------------------------- #
    # Show details — power users can inspect the numbers behind the charts
    # ----------------------------------------------------------------------- #
    with st.expander("Show details — underlying data for these charts", expanded=False):
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            st.markdown("**Monthly disease trend**")
            st.dataframe(
                trend[["period", "total_reported_cases"]].rename(
                    columns={"period": "Month", "total_reported_cases": "Total Reported Cases"}
                ),
                use_container_width=True, height=220, hide_index=True,
            )
            st.markdown("**Monthly outcome comparison**")
            st.dataframe(
                outcome[["period", "active_cases", "recovered_cases", "deaths"]].rename(
                    columns={"period": "Month", "active_cases": "Active",
                             "recovered_cases": "Recovered", "deaths": "Deaths"}
                ),
                use_container_width=True, height=220, hide_index=True,
            )
        with _dc2:
            st.markdown("**State ranking** (sorted by total reported cases)")
            st.dataframe(
                rank.reset_index().rename(columns={"index": "#"}),
                use_container_width=True, height=300, hide_index=True,
            )

    st.caption(
        f"Showing {len(df):,} surveillance records across {df['state_name'].nunique()} states, "
        f"{df['disease_name'].nunique()} diseases. Data source: fact_disease_surveillance"
    )

# =============================================================================== #
# TAB 2 — Disease Surveillance
# =============================================================================== #
with tab_surveillance:
    surv = df  # already filtered above with the shared sidebar filters
    outbreak = apply_common_filters(
        get_outbreak_master(),
        states=filters["states"], regions=filters["regions"], years=filters["years"],
        months=filters["months"], diseases=filters["diseases"],
        disease_categories=filters["disease_categories"], sources=filters["sources"],
    )
    lab = apply_common_filters(
        get_lab_master(),
        states=filters["states"], regions=filters["regions"], years=filters["years"],
        months=filters["months"],
    )

    active_outbreaks = int((outbreak["new_outbreak_flag"].astype(str).str.lower() == "yes").sum()) if not outbreak.empty else 0
    controlled_outbreaks = int((outbreak["controlled_flag"].astype(str).str.lower() == "yes").sum()) if not outbreak.empty else 0
    avg_positivity = round(lab["positivity_rate"].mean(), 2) if not lab.empty else 0.0

    # ----------------------------------------------------------------------- #
    # KPI Row
    # ----------------------------------------------------------------------- #
    sk1, sk2, sk3, sk4, sk5 = st.columns(5, gap="medium")
    with sk1:
        kpi_card("Total Reported Cases", format_number(kpis["total_reported_cases"]), bg="#EBF5FB")
        drill_button("geographic", None, key="drill_surv_total", label="↗ Geographic")
    with sk2:
        kpi_card("Active Outbreaks Flagged", format_number(active_outbreaks), color=WARNING, bg="#FDEBD0")
        drill_button("outbreak", {"status_filter": "Active"}, key="drill_surv_active",
                     label="↗ Outbreaks (active only)", help_text="Jump to Outbreak Monitoring filtered to active/new outbreaks.")
    with sk3:
        kpi_card("Outbreaks Controlled", format_number(controlled_outbreaks), color=SUCCESS, bg="#D5F5E3")
        drill_button("outbreak", {"status_filter": "Controlled"}, key="drill_surv_controlled",
                     label="↗ Outbreaks (controlled)", help_text="Jump to Outbreak Monitoring filtered to controlled outbreaks.")
    with sk4:
        kpi_card("Avg. Test Positivity Rate", f"{avg_positivity}%", color=DANGER, bg="#F5B7B1")
        drill_button("laboratory", None, key="drill_surv_pos", label="↗ Laboratory & Healthcare")
    with sk5:
        kpi_card("Case Fatality Rate", f'{kpis["case_fatality_rate"]}%', color=DANGER, bg="#FADBD8")
        drill_button("outbreak", None, key="drill_surv_cfr", label="↗ Outbreak Monitoring")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------------- #
    # Row 1 — Disease-wise trend & Top diseases
    # ----------------------------------------------------------------------- #
    sc1, sc2 = st.columns([2, 1], gap="large")

    with sc1:
        section_title("Disease-wise Case Trend", "Monthly reported cases by disease")
        all_diseases = sorted(surv["disease_name"].dropna().unique().tolist())
        default_diseases = [d for d in ["Nipah Virus", "Dengue"] if d in all_diseases]
        picked_diseases = st.multiselect(
            "Diseases shown on trend chart", options=all_diseases, default=default_diseases,
            key="trend_disease_picker",
        )
        trend_s = (
            surv[surv["disease_name"].isin(picked_diseases)]
            .groupby(["year", "month_num", "month_name", "disease_name"], as_index=False)
            ["total_reported_cases"].sum().sort_values(["year", "month_num"])
        )
        if trend_s.empty:
            st.info("Select at least one disease to display the trend.")
        else:
            trend_s["period"] = trend_s["month_name"].str[:3] + " " + trend_s["year"].astype(str)
            period_order = (
                trend_s[["year", "month_num", "period"]].drop_duplicates()
                .sort_values(["year", "month_num"])["period"].tolist()
            )

            # Built manually (rather than px.line) so every disease keeps its
            # own fixed color across reruns. Earlier versions also shaded a
            # translucent fill under every line — with 4-6 diseases those
            # fills stacked on top of each other and made the whole chart
            # read as a muddy, clumsy block wherever series crossed or sat
            # close together. Plain lines + markers stay crisp regardless of
            # how many diseases are selected, and hovermode="x unified"
            # already gives an exact per-series readout without needing the
            # fill as a visual crutch.
            if len(picked_diseases) > 8:
                st.caption(
                    "Showing the first 8 selected diseases — pick fewer for a cleaner comparison."
                )
                picked_diseases = picked_diseases[:8]

            fig = go.Figure()
            for i, disease in enumerate(picked_diseases):
                d = trend_s[trend_s["disease_name"] == disease].set_index("period").reindex(period_order).reset_index()
                color = TREND_PALETTE[i % len(TREND_PALETTE)]
                fig.add_trace(go.Scatter(
                    x=d["period"], y=d["total_reported_cases"], name=disease,
                    mode="lines+markers", line=dict(width=2.5, color=color, shape="linear"),
                    marker=dict(size=5, color=color, line=dict(width=1, color="white")),
                    hovertemplate="%{x}<br><b>%{y:,.0f}</b> cases<extra>" + disease + "</extra>",
                ))
            fig.update_layout(
                height=420, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                paper_bgcolor="white", legend_title="Disease", hovermode="x unified",
                xaxis_title=None, yaxis_title="Total Reported Cases",
                font=dict(color="#000000", size=12),
                xaxis=dict(showgrid=False, categoryorder="array", categoryarray=period_order,
                           tickfont=dict(color="#000000", size=11), linecolor="#CBD5E1"),
                yaxis=dict(showgrid=True, gridcolor="#E4EAF0", zeroline=False,
                           tickfont=dict(color="#000000", size=11)),
                legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                            font=dict(size=11, color="#000000")),
                hoverlabel=dict(font=dict(color="#000000"), bgcolor="white"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with sc2:
        section_title("Top Diseases by Burden", "Total reported cases · 💡 click a bar to filter the page to that disease")
        top_disease = surv.groupby("disease_name", as_index=False)["total_reported_cases"].sum().sort_values(
            "total_reported_cases", ascending=True
        ).tail(10)
        fig_top = px.bar(top_disease, x="total_reported_cases", y="disease_name", orientation="h",
                          color="total_reported_cases", color_continuous_scale=NAVY_TEAL_SCALE,
                          custom_data=["disease_name"])
        fig_top.update_traces(
            hovertemplate="%{y}<br>Total cases: <b>%{x:,.0f}</b><br><i>👆 click to filter</i><extra></extra>"
        )
        fig_top.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False,
                               yaxis_title=None, xaxis_title="Total Reported Cases")
        _ev_top = st.plotly_chart(fig_top, use_container_width=True, on_select="rerun", selection_mode=["points"])
        _rows_top = clicked_customdata_rows(_ev_top)
        if _rows_top:
            stage_filter_updates({"f_disease": [_rows_top[0][0]]}, origin_label="Disease")

    # ----------------------------------------------------------------------- #
    # Row 2 — State x Disease heatmap & Reporting Source mix
    # ----------------------------------------------------------------------- #
    sc3, sc4 = st.columns([2, 1], gap="large")

    with sc3:
        section_title("State × Disease Hotspot Matrix", "Total reported cases — green = low burden, yellow = medium, red = high burden")
        pivot = surv.pivot_table(index="state_name", columns="disease_name",
                                  values="total_reported_cases", aggfunc="sum", fill_value=0)
        top_states = surv.groupby("state_name")["total_reported_cases"].sum().sort_values(ascending=False).head(15).index
        pivot = pivot.loc[pivot.index.intersection(top_states)]
        # Cell values are dense (15 states x many diseases), so printing a
        # number in every cell would overlap and hurt readability rather
        # than help it — instead we make sure every label around the grid
        # (axis ticks, colorbar) is explicitly dark and legible, and rely
        # on hover for the exact figure per cell.
        fig_heat = px.imshow(pivot, color_continuous_scale=RISK_HEATMAP_SCALE, aspect="auto")
        fig_heat.update_traces(
            hovertemplate="State: %{y}<br>Disease: %{x}<br>Cases: %{z:,.0f}<extra></extra>",
            xgap=2, ygap=2,
        )
        fig_heat.update_layout(
            height=440, margin=dict(l=10, r=10, t=20, b=10),
            font=dict(color="#000000", size=11),
            xaxis=dict(tickfont=dict(color="#000000", size=10), side="bottom"),
            yaxis=dict(tickfont=dict(color="#000000", size=10)),
            coloraxis_colorbar=dict(title=dict(text="Cases", font=dict(color="#000000")), tickfont=dict(color="#000000")),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        with st.expander("Show details — state × disease matrix", expanded=False):
            st.dataframe(
                pivot.reset_index().rename(columns={"index": "State"}),
                use_container_width=True, height=280,
            )

    with sc4:
        section_title("Reports by Source", "Share of records by reporting channel")
        src_mix = surv.groupby("source_name", as_index=False)["total_reported_cases"].sum()
        fig_src = px.pie(src_mix, names="source_name", values="total_reported_cases", hole=0.5,
                          color_discrete_sequence=BRAND_SEQUENCE)
        fig_src.update_traces(
            textinfo="percent+label", textposition="outside",
            textfont=dict(color="#000000", size=12),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} cases (%{percent:.1%})<extra></extra>",
        )
        fig_src.update_layout(height=440, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(fig_src, use_container_width=True)

    # ----------------------------------------------------------------------- #
    # Row 3 — Outbreak alert table & Testing performance
    # ----------------------------------------------------------------------- #
    sc5, sc6 = st.columns(2, gap="large")

    with sc5:
        section_title("Recent Outbreak Alerts", "Highest alert level, most recent first")
        if not outbreak.empty:
            alert_order = {"High": 0, "Moderate": 1, "Low": 2}
            alerts = outbreak.copy()
            alerts["_rank"] = alerts["alert_level"].map(alert_order).fillna(3)
            alerts = alerts.sort_values(["_rank", "full_date"], ascending=[True, False]).head(12)
            show = alerts[["full_date", "state_name", "disease_name", "alert_level",
                            "containment_rate_pct", "response_time_hours", "controlled_flag"]].rename(
                columns={
                    "full_date": "Date", "state_name": "State", "disease_name": "Disease",
                    "alert_level": "Alert Level", "containment_rate_pct": "Containment %",
                    "response_time_hours": "Response (hrs)", "controlled_flag": "Controlled",
                }
            )
            show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")

            def highlight_alert(val):
                color = {"High": "#F7DEDE", "Moderate": "#F6E9CC", "Low": "#DCEBE4"}.get(val, "")
                return f"background-color: {color}"

            styled_alerts = show.style.map(highlight_alert, subset=["Alert Level"])
            st.dataframe(styled_alerts, use_container_width=True, height=400, hide_index=True)
        else:
            st.info("No outbreak records for the current filter selection.")

    with sc6:
        section_title("Testing Volume vs Positivity Rate", "By state · 💡 click a state to filter the page")
        if not lab.empty:
            lab_state = lab.groupby("state_name", as_index=False).agg(
                total_tests=("total_tests", "sum"), positivity_rate=("positivity_rate", "mean")
            ).sort_values("total_tests", ascending=False).head(15)
            _lab_rows = [[s] for s in lab_state["state_name"].astype(str).tolist()]
            fig_lab = go.Figure()
            fig_lab.add_bar(x=lab_state["state_name"], y=lab_state["total_tests"], name="Total Tests",
                             marker_color=PRIMARY, yaxis="y1", customdata=_lab_rows,
                             hovertemplate="%{x}<br>Total tests: <b>%{y:,.0f}</b><br><i>👆 click to filter</i><extra></extra>")
            fig_lab.add_trace(go.Scatter(x=lab_state["state_name"], y=lab_state["positivity_rate"],
                                          name="Positivity Rate (%)", yaxis="y2",
                                          mode="lines+markers", line=dict(color=DANGER, width=3),
                                          customdata=_lab_rows,
                                          hovertemplate="%{x}<br>Positivity rate: <b>%{y:.1f}%</b><br><i>👆 click to filter</i><extra></extra>"))
            fig_lab.update_layout(
                height=400, margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(title="Total Tests"),
                yaxis2=dict(title="Positivity Rate (%)", overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                xaxis_tickangle=-35, plot_bgcolor="white", paper_bgcolor="white",
            )
            _ev_lab = st.plotly_chart(fig_lab, use_container_width=True, on_select="rerun", selection_mode=["points"])
            _rows_lab = clicked_customdata_rows(_ev_lab)
            if _rows_lab:
                stage_filter_updates({"f_state": [_rows_lab[0][0]]}, origin_label="State")
            with st.expander("Show details — testing performance by state", expanded=False):
                st.dataframe(
                    lab_state.rename(columns={"state_name": "State", "total_tests": "Total Tests",
                                              "positivity_rate": "Positivity Rate (%)"}),
                    use_container_width=True, height=260, hide_index=True,
                )
        else:
            st.info("No lab/testing records for the current filter selection.")

    st.caption(
        f"Showing {len(surv):,} surveillance records · {len(outbreak):,} outbreak records · "
        f"{len(lab):,} lab/testing records for the selected filters."
    )

