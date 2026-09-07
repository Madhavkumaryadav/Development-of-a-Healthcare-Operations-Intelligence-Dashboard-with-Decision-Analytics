"""
interactivity.py
----------------
Small shared helpers that make the HealthSentinel dashboards interactive
without leaving Streamlit's native component set:

* drill-down navigation between st.Page dashboards (session_state carries
  the prefill across the switch),
* "staged" filter updates: Streamlit forbids mutating a widget's
  session_state key *after* that widget has been instantiated in the same
  run. Chart click-selections happen after the page's filter widgets were
  drawn, so the update is queued here under a non-widget key and applied at
  the very top of the next run, before any widget is created.
* parsing Plotly ``on_select`` events into the values embedded in each
  point's ``customdata``,
* a visible "clear selection" strip so a click-filter is never a hidden
  interaction the user has to guess about.

Pages call :func:`handle_page_enter` at the very top of their script (right
after imports / CSS injection) to (a) honor pending drill-down requests and
(b) consume any staged click-filter updates before reading filter state.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st


# --------------------------------------------------------------------------- #
# Drill-down navigation
# --------------------------------------------------------------------------- #
# app.py builds all of its st.Page objects once per run; it registers them
# here under stable keys so any dashboard can programmatically navigate to
# another dashboard via st.switch_page(page_object) — the API that is
# guaranteed to work with st.navigation apps.
PAGE_REGISTRY: dict[str, st.Page] = {}


def register_pages(pages: dict[str, st.Page]) -> None:
    """Called by app.py with {"outbreak": st.Page(...), ...} before pg.run()."""
    PAGE_REGISTRY.update(pages)


def _request_drill_down(page_key: str, prefill: dict[str, Any] | None = None) -> None:
    """Button on_click target: remember which page we want and what its
    filter keys should be prefilled with. The actual switch happens on the
    next rerun, from the top of the current page (handle_page_enter), where
    st.switch_page is legal."""
    st.session_state["_nav_request"] = {
        "page": page_key,
        "prefill": prefill or {},
    }


def drill_button(
    page_key: str,
    prefill: dict[str, Any] | None = None,
    key: str | None = None,
    label: str | None = None,
    help_text: str | None = None,
    use_container_width: bool = True,
) -> None:
    """A small, obviously-clickable button under a KPI card / summary that
    jumps to another dashboard with optional filter prefills."""
    page = PAGE_REGISTRY.get(page_key)
    target_name = page.title if page is not None else page_key.replace("_", " ").title()
    default_label = f"Open in {target_name} →"
    st.button(
        label or default_label,
        key=key or f"drill_{page_key}_{hash((page_key, str(prefill))) % 100000}",
        on_click=_request_drill_down,
        args=(page_key, prefill),
        use_container_width=use_container_width,
        help=help_text or f"Jump to the {target_name} dashboard, keeping the current selection.",
    )


def handle_pending_drill() -> bool:
    """If a drill-down was requested (button clicked on the previous run),
    apply its prefill to the target page's filter keys and switch page.
    Call at the top of every dashboard page. Returns True when the page
    should stop (st.switch_page already stopped execution)."""
    nav = st.session_state.pop("_nav_request", None)
    if not nav:
        return False
    page = PAGE_REGISTRY.get(nav.get("page"))
    if page is None:
        return False
    for key, value in (nav.get("prefill") or {}).items():
        # Widgets of the target page are not created yet in this run, so
        # writing their session_state keys is always legal here.
        st.session_state[key] = value
    # Never carry a page's pending click-filters into the page we navigate to.
    st.session_state.pop("_pending_filter_updates", None)
    st.switch_page(page)
    return True


def handle_page_enter() -> bool:
    """Top-of-page hook for every dashboard page: honors a pending
    drill-down navigation and then applies any staged click-filter updates
    before the page reads its filter state or draws filter widgets."""
    if handle_pending_drill():
        return True
    consume_pending_filter_updates()
    return False


# --------------------------------------------------------------------------- #
# Staged filter updates (chart clicks happen after widgets were drawn)
# --------------------------------------------------------------------------- #
def stage_filter_updates(updates: dict[str, Any], origin_label: str | None = None) -> None:
    """Queue widget-key updates that cannot be applied right now (because
    the widget with that key already exists in this run). They are applied
    by consume_pending_filter_updates() at the top of the next rerun.

    ``origin_label`` (e.g. "State") marks the dimension as having come from
    a chart click, so the clear-selection strip can show a targeted ✕ chip.
    """
    pending = dict(st.session_state.get("_pending_filter_updates", {}))
    pending.update(updates)
    st.session_state["_pending_filter_updates"] = pending
    if origin_label:
        origins = dict(st.session_state.get("_click_origin", {}))
        for key in updates:
            origins[key] = origin_label
        st.session_state["_click_origin"] = origins


def consume_pending_filter_updates() -> None:
    """Apply queued filter updates. Must run before any filter widget is
    instantiated (put right at the top of each dashboard page)."""
    pending = st.session_state.pop("_pending_filter_updates", None)
    if not pending:
        return
    for key, value in pending.items():
        st.session_state[key] = value


def clear_dimension_keys(clear_map: dict[str, Any]) -> None:
    """on_click target for the ✕ chips: reset the given widget keys and
    forget that they came from a chart click."""
    origins = dict(st.session_state.get("_click_origin", {}))
    for key in clear_map:
        origins.pop(key, None)
    st.session_state["_click_origin"] = origins
    # Route through the staged mechanism so widget-key mutation only happens
    # before widgets are created on the next run.
    stage_filter_updates(clear_map)


def render_click_clear_strip(dims: list[dict[str, Any]]) -> None:
    """Render a visible 'click-selection active' strip with one ✕ chip per
    dimension that was set by a chart click. ``dims`` is a list of dicts:

        {
          "label": "State",                       # chip text label
          "key": "f_state",                       # the widget session key
          "current": [...],                       # current non-default value(s)
          "clear": {"f_state": []},               # key -> default on clear
        }

    Nothing renders when no click-origin dimension is currently active, so
    the full-data view stays clean.
    """
    origins = st.session_state.get("_click_origin", {})
    active = []
    for dim in dims:
        key = dim["key"]
        if key not in origins:
            continue
        current = dim.get("current")
        if current is None or current == [] or current == "" or current == "All":
            continue
        active.append(dim)

    if not active:
        return

    st.markdown(
        "<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:2px 0 6px;'>"
        "<span style='font-size:0.8rem;font-weight:700;color:#17324D;'>👆 Chart click-selection active — "
        "every chart & KPI below is filtered to:</span></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(active), gap="small")
    for col, dim in zip(cols, active):
        current = dim.get("current")
        if isinstance(current, (list, tuple)):
            display = ", ".join(str(v) for v in current)
        else:
            display = str(current)
        with col:
            st.button(
                f"✕ {dim.get('label', '')}: {display}",
                key=f"clear_click_{dim['key']}",
                on_click=clear_dimension_keys,
                args=(dim["clear"],),
                use_container_width=True,
                help=f"Clear the {dim.get('label', '')} click-selection and return to the full dataset.",
            )


# --------------------------------------------------------------------------- #
# Plotly selection parsing
# --------------------------------------------------------------------------- #
def clicked_values(event: dict | None) -> list[str]:
    """Extract the values embedded in customdata[0] of every point in a
    Plotly selection event. Returns [] when nothing was clicked."""
    if not event:
        return []
    points = (event.get("selection") or {}).get("points") or []
    values: list[str] = []
    for point in points:
        cd = point.get("customdata")
        if isinstance(cd, (list, tuple)) and cd:
            v = cd[0]
        else:
            v = cd
        if v is None:
            continue
        values.append(str(v))
    return values


def clicked_customdata_rows(event: dict | None) -> list[list]:
    """Return each clicked point's full customdata row (useful when a chart
    embeds several lookup columns, e.g. [year, month_name])."""
    if not event:
        return []
    points = (event.get("selection") or {}).get("points") or []
    rows: list[list] = []
    for point in points:
        cd = point.get("customdata")
        if isinstance(cd, (list, tuple)) and cd:
            rows.append([str(c) if c is not None else None for c in cd])
        elif cd is not None:
            rows.append([str(cd)])
    return rows


# --------------------------------------------------------------------------- #
# MoM delta formatting helpers (pure)
# --------------------------------------------------------------------------- #
def pct_delta(cur: float, prev: float | None, suffix: str = "MoM", decimals: int = 1) -> str | None:
    """Percent change from prev to cur, formatted '+3.4% MoM' (None when
    there is nothing to compare against)."""
    if prev is None or prev == 0:
        return None
    try:
        return f"{(float(cur) - float(prev)) / abs(float(prev)) * 100:+.{decimals}f}% {suffix}"
    except (TypeError, ValueError):
        return None


def pp_delta(cur: float, prev: float | None, suffix: str = "MoM", decimals: int = 2) -> str | None:
    """Percentage-point (or absolute) difference, formatted '+2.10 MoM'."""
    if prev is None:
        return None
    try:
        return f"{float(cur) - float(prev):+.{decimals}f} {suffix}"
    except (TypeError, ValueError):
        return None


def latest_two_rows(df, date_col: str = "full_date"):
    """Return (current_row, previous_row) aggregated per calendar month for
    the last two months present in ``df``. Rows are dicts with the numeric
    columns summed, plus 'year'/'month_num'. Both are None when the frame
    has fewer than two months."""
    if df is None or df.empty or date_col not in df.columns:
        return None, None
    tmp = df.dropna(subset=[date_col])
    if tmp.empty:
        return None, None
    month_series = pd.to_datetime(tmp[date_col]).dt.to_period("M")
    order = sorted(month_series.unique())
    if len(order) < 1:
        return None, None
    cur_period = order[-1]
    cur = tmp[month_series == cur_period]
    prev_period = order[-2] if len(order) > 1 else None
    prev = tmp[month_series == prev_period] if prev_period is not None else None
    return cur, prev


def mom_delta_text(
    cur_df,
    prev_df,
    column: str,
    agg: str = "sum",
    kind: str = "pct",
    suffix: str = "MoM",
    decimals: int = 1,
) -> str | None:
    """Compare one metric between the current and previous month and return
    a '+/-' delta string ready for kpi_card_delta()."""

    def _value(frame):
        if frame is None or frame.empty or column not in frame.columns:
            return None
        if agg == "mean":
            return float(frame[column].mean())
        if agg == "sum":
            return float(frame[column].sum())
        if agg == "median":
            return float(frame[column].median())
        return float(getattr(frame[column], agg)())

    cur = _value(cur_df)
    prev = _value(prev_df)
    if cur is None or prev is None:
        return None
    if kind == "pct":
        return pct_delta(cur, prev, suffix=suffix, decimals=decimals)
    return pp_delta(cur, prev, suffix=suffix, decimals=decimals)


def select_hint() -> str:
    """Text used inside Plotly hovertemplates to advertise clickability."""
    return "<i>👆 click to filter this page</i>"
