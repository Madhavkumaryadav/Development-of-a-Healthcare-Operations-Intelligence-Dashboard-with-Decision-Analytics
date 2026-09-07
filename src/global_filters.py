"""
global_filters.py
-----------------
A "Global scope" panel pinned in the sidebar (rendered once from app.py, so
it survives page navigation) that narrows the entire dashboard suite by
state, disease, and a date window. Selections live in session_state under
``gs_*`` keys and are applied by each data dashboard on top of its own
page-level filters via :func:`apply_global_scope`.

The sidebar also carries a free-text search box that deliberately uses an
Apply-button pattern (not per-keystroke recompute) so typing never triggers
an expensive full-app rerun until the user commits.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import get_filter_options, load_raw_tables

# Widget/session keys owned by this module (namespaced gs_* so they never
# collide with page-level filter keys like f_state / state_filter).
K_STATES = "gs_states"
K_DISEASES = "gs_diseases"
K_FROM = "gs_from"
K_TO = "gs_to"
K_TEXT_RAW = "gs_text_raw"     # text box contents (not applied until "Apply")
K_TEXT = "gs_text"             # committed search text (applies to pages)

EMPTY_FLAG = "_gs_scope_missed"

_PANEL_CSS = f"""
<style>
    .gs-title {{
        color: #FFFFFF; font-weight: 800; font-size: 1.0rem; margin: 0 0 2px 0;
    }}
    .gs-sub {{
        color: rgba(255,255,255,0.75); font-size: 0.74rem; line-height: 1.4; margin-bottom: 8px;
    }}
    .gs-active-box {{
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18);
        border-radius: 8px; padding: 8px 10px; margin: 8px 0 4px 0;
        color: #FFFFFF; font-size: 0.74rem; line-height: 1.5;
    }}
    .gs-active-box b {{ color: #FFC24B; }}
    .gs-warn {{
        background: rgba(255, 201, 106, 0.16); border: 1px solid rgba(255, 201, 106, 0.5);
        border-radius: 8px; padding: 7px 10px; margin: 6px 0 2px 0;
        color: #FFE7B8; font-size: 0.72rem; line-height: 1.45;
    }}
</style>
"""


# --------------------------------------------------------------------------- #
# Option universe (from the shared data loader so every page agrees)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False, ttl=600)
def _scope_options():
    opts = get_filter_options()
    dates = load_raw_tables()["dim_dates"]
    months = sorted(dates["year_month"].dropna().astype(str).unique().tolist())
    return {
        "states": opts["states"],
        "diseases": opts["diseases"],
        "months": months,
    }


# --------------------------------------------------------------------------- #
# State access
# --------------------------------------------------------------------------- #
def ensure_scope_state() -> dict:
    """Seed every gs_* key with sensible defaults and return current scope."""
    opts = _scope_options()
    months = opts["months"]
    default_from = months[0] if months else "2022-01"
    default_to = months[-1] if months else "2024-12"
    st.session_state.setdefault(K_STATES, [])
    st.session_state.setdefault(K_DISEASES, [])
    st.session_state.setdefault(K_FROM, default_from)
    st.session_state.setdefault(K_TO, default_to)
    st.session_state.setdefault(K_TEXT, "")
    st.session_state.setdefault(K_TEXT_RAW, "")
    return get_global_scope()


def _sanitize_scope():
    """Clamp values before widgets are drawn (widgets read session_state)."""
    opts = _scope_options()
    months = opts["months"]
    if not months:
        return
    state_from = st.session_state.get(K_FROM)
    state_to = st.session_state.get(K_TO)
    if state_from not in months:
        st.session_state[K_FROM] = months[0]
    if state_to not in months:
        st.session_state[K_TO] = months[-1]
    # Keep From <= To.
    if months.index(st.session_state[K_FROM]) > months.index(st.session_state[K_TO]):
        st.session_state[K_TO] = st.session_state[K_FROM]


def get_global_scope() -> dict:
    """Current scope dict with normalized keys (states/diseases lists,
    from/to 'YYYY-MM' strings, text string)."""
    opts = _scope_options()
    months = opts["months"]
    default_from = months[0] if months else "2022-01"
    default_to = months[-1] if months else "2024-12"
    states = list(st.session_state.get(K_STATES, []) or [])
    diseases = list(st.session_state.get(K_DISEASES, []) or [])
    state_from = st.session_state.get(K_FROM, default_from)
    state_to = st.session_state.get(K_TO, default_to)
    if state_from not in months:
        state_from = default_from
    if state_to not in months:
        state_to = default_to
    return {
        "states": [s for s in states if s],
        "diseases": [d for d in diseases if d],
        "from": state_from,
        "to": state_to,
        "text": str(st.session_state.get(K_TEXT, "") or "").strip(),
    }


def scope_is_active(scope: dict | None = None) -> bool:
    scope = scope or get_global_scope()
    opts = _scope_options()
    months = opts["months"]
    full_range = bool(months) and scope["from"] == months[0] and scope["to"] == months[-1]
    return bool(scope["states"] or scope["diseases"] or scope["text"] or not full_range)


def scope_summary_lines(scope: dict | None = None) -> list[str]:
    """Human-readable lines describing the active scope (for chips/notes)."""
    scope = scope or get_global_scope()
    opts = _scope_options()
    months = opts["months"]
    lines = []
    if scope["states"]:
        lines.append(f"{len(scope['states'])} state(s)")
    if scope["diseases"]:
        lines.append(f"{len(scope['diseases'])} disease(s)")
    if scope["text"]:
        lines.append(f'search “{scope["text"]}”')
    full_range = bool(months) and scope["from"] == months[0] and scope["to"] == months[-1]
    if not full_range:
        lines.append(f"{scope['from']} → {scope['to']}")
    return lines


def _clear_all():
    st.session_state[K_STATES] = []
    st.session_state[K_DISEASES] = []
    st.session_state[K_TEXT] = ""
    st.session_state[K_TEXT_RAW] = ""
    opts = _scope_options()
    months = opts["months"]
    if months:
        st.session_state[K_FROM] = months[0]
        st.session_state[K_TO] = months[-1]
    st.session_state.pop(EMPTY_FLAG, None)


def _apply_search():
    st.session_state[K_TEXT] = str(st.session_state.get(K_TEXT_RAW, "") or "").strip()


# --------------------------------------------------------------------------- #
# Sidebar panel
# --------------------------------------------------------------------------- #
def render_global_scope_panel() -> None:
    """Draw the pinned sidebar panel. Called from app.py once per run, so
    it appears on every page of the suite."""
    if not st.session_state.get("authenticated"):
        return
    st.markdown(_PANEL_CSS, unsafe_allow_html=True)
    ensure_scope_state()
    _sanitize_scope()

    opts = _scope_options()
    months = opts["months"]
    scope = get_global_scope()

    with st.sidebar:
        st.markdown("---")
        st.markdown('<div class="gs-title">🌐 Global scope</div>')
        st.markdown(
            '<div class="gs-sub">Optional context applied to the data dashboards '
            "(0–4) below, stacked on top of each page's own filters.</div>",
            unsafe_allow_html=True,
        )

        st.text_input(
            "Search state / disease",
            key=K_TEXT_RAW,
            placeholder="e.g. dengue or Maharashtra…",
            label_visibility="collapsed",
        )
        apply_col, clear_search_col = st.columns([1, 1])
        with apply_col:
            st.button(
                "Apply search",
                key="gs_apply_search",
                use_container_width=True,
                on_click=_apply_search,
            )
        with clear_search_col:
            st.button(
                "Clear",
                key="gs_clear_text",
                use_container_width=True,
                on_click=_clear_all,
            )

        st.multiselect("States", opts["states"], key=K_STATES)
        st.multiselect("Diseases", opts["diseases"], key=K_DISEASES)

        if months:
            st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
            st.caption("Date window (YYYY-MM)")
            from_col, to_col = st.columns(2)
            with from_col:
                st.selectbox("From", months, key=K_FROM, label_visibility="collapsed")
            with to_col:
                st.selectbox("To", months, key=K_TO, label_visibility="collapsed")

        if scope_is_active(scope):
            lines = scope_summary_lines(scope)
            box = "<div class='gs-active-box'><b>Active scope:</b> " + " · ".join(lines)
            box += "<br><span style='color:rgba(255,255,255,0.55)'>Clearing returns pages to the full dataset.</span></div>"
            st.markdown(box, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='gs-active-box'><b>All available data</b> — no global scope applied.</div>",
                unsafe_allow_html=True,
            )

        if st.session_state.get(EMPTY_FLAG):
            st.markdown(
                "<div class='gs-warn'>⚠️ The active scope matches no rows in the data "
                "on this page — it has been ignored here so the dashboard can still "
                "render. Broaden the scope above to filter everywhere.</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div style='color:rgba(255,255,255,0.45);font-size:0.65rem;margin-top:2px;'>"
            f"Scope keys: states · diseases · date window · search</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Applying the scope to a page's dataframe
# --------------------------------------------------------------------------- #
def _date_bounds(scope: dict):
    from pandas import Timestamp

    start = Timestamp(scope["from"] + "-01")
    end = (Timestamp(scope["to"] + "-01") + pd.offsets.MonthEnd(0)).normalize()
    return start, end


def apply_global_scope(
    df: pd.DataFrame,
    *,
    state_col: str = "state_name",
    disease_col: str = "disease_name",
    date_col: str = "full_date",
    year_col: str = "year",
    month_col: str = "month_num",
    scope: dict | None = None,
) -> pd.DataFrame:
    """Filter ``df`` by the current global scope (stacks on the caller's own
    filters). Column names can be overridden for pages with a different
    naming scheme (e.g. the Health Programs frame uses ``State``/``Year``).

    If the scope would empty the frame the scope is skipped for this frame
    and a note is surfaced in the sidebar panel — an empty dashboard is
    never an acceptable outcome of the *global* controls.
    """
    if df is None or df.empty:
        return df
    scope = scope or get_global_scope()
    if not scope_is_active(scope):
        st.session_state.pop(EMPTY_FLAG, None)
        return df

    out = df.copy()
    filters_applied = 0

    if scope["states"] and state_col in out.columns:
        out = out[out[state_col].isin(scope["states"])]
        filters_applied += 1
    if scope["diseases"] and disease_col in out.columns:
        out = out[out[disease_col].isin(scope["diseases"])]
        filters_applied += 1

    text = scope["text"]
    if text:
        text_cols = [c for c in (state_col, disease_col) if c in out.columns]
        if text_cols:
            mask = pd.Series(False, index=out.index)
            for col in text_cols:
                mask |= out[col].astype(str).str.contains(text, case=False, na=False)
            out = out[mask]
            filters_applied += 1

    opts = _scope_options()
    months = opts["months"]
    date_full = bool(months) and not (scope["from"] == months[0] and scope["to"] == months[-1])
    if date_full:
        if date_col in out.columns and pd.api.types.is_datetime64_any_dtype(out[date_col]):
            start, end = _date_bounds(scope)
            out = out[(out[date_col] >= start) & (out[date_col] <= end)]
            filters_applied += 1
        elif year_col in out.columns and month_col in out.columns:
            # Month name is available in some frames; month_num is a safe
            # numeric key in both naming schemes.
            if month_col in out.columns:
                start, end = _date_bounds(scope)
                ym = (
                    out[year_col].astype(int).astype(str)
                    + "-"
                    + out[month_col].astype(int).astype(str).str.zfill(2)
                )
                out = out[(ym >= start.strftime("%Y-%m")) & (ym <= end.strftime("%Y-%m"))]
                filters_applied += 1

    if filters_applied == 0:
        st.session_state.pop(EMPTY_FLAG, None)
        return df

    if out.empty:
        st.session_state[EMPTY_FLAG] = True
        return df
    st.session_state.pop(EMPTY_FLAG, None)
    return out


def render_scope_note(prefix: str = "") -> None:
    """Small note shown on each page header area when a global scope is
    active, so users understand why the page is narrowed even when every
    page-level filter reads 'All'."""
    scope = get_global_scope()
    if not scope_is_active(scope):
        return
    lines = scope_summary_lines(scope)
    st.markdown(
        f"<div class='active-filter-summary' style='margin-top:4px;'>"
        f"<span class='summary-label'>🌐 Global scope:</span>"
        f"{''.join(f'<span class=\"active-filter-chip\">{line}</span>' for line in lines)}"
        f"</div>",
        unsafe_allow_html=True,
    )
