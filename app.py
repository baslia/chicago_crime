"""Chicago Crime Dashboard — an open-source Streamlit app over Chicago open data.

Run locally:
    streamlit run app.py

Data: City of Chicago "Crimes - 2001 to Present" via the Socrata SODA API.
An app token is optional (higher rate limits); set SOCRATA_APP_TOKEN if you have one.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st
from streamlit_folium import st_folium

from src import charts, config, data

st.set_page_config(
    page_title="Chicago Crime Dashboard",
    page_icon="🚔",
    layout="wide",
)


# --- sidebar filters ----------------------------------------------------------
def sidebar_filters() -> dict:
    st.sidebar.title("🚔 Chicago Crime")
    st.sidebar.caption("Open data · City of Chicago (SODA API)")

    today = date.today()
    default_start = date(today.year, 1, 1)
    # Seed the shared date-range state once; the picker and presets both use it.
    if "date_range" not in st.session_state:
        st.session_state["date_range"] = (default_start, today)

    st.sidebar.markdown("**Date range**")
    presets = {
        "30d": lambda: (today - timedelta(days=30), today),
        "90d": lambda: (today - timedelta(days=90), today),
        "YTD": lambda: (date(today.year, 1, 1), today),
        "1y": lambda: (today - timedelta(days=365), today),
        "All": lambda: (date(config.MIN_YEAR, 1, 1), today),
    }
    # Compact pill shortcuts. Apply a preset only when the selection *changes* so
    # it's applied once and never fights a later manual edit of the picker.
    choice = st.sidebar.pills(
        "Quick range", options=list(presets), selection_mode="single",
        key="date_preset", label_visibility="collapsed",
    )
    if choice and choice != st.session_state.get("_applied_preset"):
        st.session_state["_applied_preset"] = choice
        st.session_state["date_range"] = presets[choice]()

    picked = st.sidebar.date_input(
        "Date range",
        key="date_range",
        min_value=date(config.MIN_YEAR, 1, 1),
        max_value=today,
        label_visibility="collapsed",
        help="Analytics aggregate across this whole range; the map shows the "
        "most recent matching incidents up to the marker cap.",
    )
    # date_input returns a 1-tuple mid-selection, a 2-tuple once both ends are set.
    if isinstance(picked, tuple) and len(picked) == 2:
        start, end = picked
    else:
        start, end = default_start, today

    st.sidebar.markdown("**Crime groups**")
    selected_groups = st.sidebar.pills(
        "Crime groups", options=list(config.CRIME_GROUPS), selection_mode="multi",
        key="crime_groups", label_visibility="collapsed",
        help="Shortcuts that expand into their underlying crime types.",
    )
    group_types = config.expand_groups(selected_groups)

    try:
        all_types = data.list_primary_types()
    except Exception:
        all_types = sorted(config.CRIME_TYPE_COLORS.keys())
    individual_types = st.sidebar.multiselect(
        "Individual types (drilldown)", options=all_types, default=[],
        help="Refine further. Combined with any selected groups.",
    )

    # Effective filter = union of expanded groups + individually picked types.
    # Empty means "all types".
    crime_types = tuple(dict.fromkeys((*group_types, *individual_types)))
    if selected_groups or individual_types:
        st.sidebar.caption(f"Filtering {len(crime_types)} crime type(s).")

    area_options = list(config.COMMUNITY_AREAS.items())
    area_labels = {f"{code} — {name}": code for code, name in area_options}
    selected_area_labels = st.sidebar.multiselect(
        "Community areas", options=list(area_labels.keys()), default=[],
        help="Leave empty for all 77 areas.",
    )
    community_areas = tuple(area_labels[label] for label in selected_area_labels)

    arrest_only = st.sidebar.toggle("Arrests only", value=False)

    st.sidebar.divider()
    token_state = "✅ app token set" if data.has_app_token() else "⚠️ no app token (rate-limited)"
    st.sidebar.caption(token_state)

    return dict(
        start=start,
        end=end,
        crime_types=tuple(crime_types),
        community_areas=community_areas,
        arrest_only=arrest_only,
    )


# --- KPI row ------------------------------------------------------------------
def kpi_row(f: dict) -> None:
    year_df = data.agg_by_year(**f)
    type_df = data.agg_by_type(**f)

    total = int(year_df["count"].sum()) if not year_df.empty else 0
    arrests = int(type_df["arrests"].sum()) if not type_df.empty else 0
    arrest_rate = (arrests / total) if total else 0.0
    top_type = type_df.iloc[0]["primary_type"] if not type_df.empty else "—"

    # Year-over-year: last two full years present in the aggregate.
    yoy = None
    if not year_df.empty and len(year_df) >= 2:
        last, prev = year_df.iloc[-1]["count"], year_df.iloc[-2]["count"]
        if prev:
            yoy = (last - prev) / prev

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total crimes", f"{total:,}")
    c2.metric("Arrest rate", f"{arrest_rate:.1%}")
    c3.metric("Most common", top_type.title() if top_type else "—")
    c4.metric(
        "YoY change",
        f"{yoy:+.1%}" if yoy is not None else "n/a",
        delta=f"{yoy:+.1%}" if yoy is not None else None,
        delta_color="inverse",  # more crime = bad
    )


# --- map tab ------------------------------------------------------------------
def map_view(f: dict) -> None:
    incidents = data.fetch_incidents(**f)
    left, right = st.columns([4, 1])

    with left:
        if incidents.empty:
            st.info("No incidents with coordinates match these filters.")
        else:
            capped = len(incidents) >= config.MAX_MAP_POINTS
            if capped:
                st.caption(
                    f"Showing the {config.MAX_MAP_POINTS:,} most recent matching "
                    "incidents (marker cap). Narrow the date range or filters for full coverage."
                )
            st_folium(
                charts.build_map(incidents),
                use_container_width=True,
                height=560,
                returned_objects=[],  # we don't need click state → avoids reruns
                key="crime_map",
            )

    with right:
        st.markdown("**Legend**")
        for crime_type, color in charts.type_legend(incidents):
            st.markdown(
                f"<span style='display:inline-block;width:10px;height:10px;"
                f"border-radius:50%;background:{color};margin-right:6px;'></span>"
                f"<span style='font-size:0.8rem'>{crime_type.title()}</span>",
                unsafe_allow_html=True,
            )


# --- analytics tabs -----------------------------------------------------------
def trends_view(f: dict) -> None:
    year_df = data.agg_by_year(**f)
    if year_df.empty:
        st.info("No data for these filters.")
        return
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.chart_by_year(year_df), use_container_width=True)
    c2.plotly_chart(charts.chart_by_month(data.agg_by_month(**f)), use_container_width=True)
    c3, c4 = st.columns(2)
    c3.plotly_chart(charts.chart_by_dow(data.agg_by_dow(**f)), use_container_width=True)
    c4.plotly_chart(charts.chart_by_hour(data.agg_by_hour(**f)), use_container_width=True)


def type_view(f: dict) -> None:
    type_df = data.agg_by_type(**f)
    if type_df.empty:
        st.info("No data for these filters.")
        return
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.chart_by_type(type_df), use_container_width=True)
    c2.plotly_chart(charts.chart_arrest_rate_by_type(type_df), use_container_width=True)
    with st.expander("View table"):
        st.dataframe(
            type_df[["primary_type", "count", "arrests", "arrest_rate"]]
            .rename(columns={"primary_type": "Type", "count": "Crimes",
                             "arrests": "Arrests", "arrest_rate": "Arrest rate"}),
            use_container_width=True, hide_index=True,
        )


def geo_view(f: dict) -> None:
    area_df = data.agg_by_community_area(**f)
    if area_df.empty:
        st.info("No data for these filters.")
        return

    st.caption("Community areas shaded by crime count — hover for details.")
    st_folium(
        charts.build_choropleth(area_df, data.community_area_geojson()),
        use_container_width=True,
        height=520,
        returned_objects=[],
        key="choropleth",
    )

    st.plotly_chart(charts.chart_by_area(area_df), use_container_width=True)
    with st.expander("View table"):
        st.dataframe(
            area_df[["area_name", "count"]].rename(
                columns={"area_name": "Community area", "count": "Crimes"}),
            use_container_width=True, hide_index=True,
        )


# --- main ---------------------------------------------------------------------
def main() -> None:
    f = sidebar_filters()

    st.title("Chicago Crime Dashboard")
    st.caption(
        f"{f['start']:%b %d, %Y} → {f['end']:%b %d, %Y} · "
        "Source: [City of Chicago Open Data]"
        "(https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)"
    )

    try:
        kpi_row(f)
    except Exception as exc:  # keep the app usable if the API hiccups
        st.warning(f"Could not load summary metrics: {exc}")

    map_tab, trends_tab, type_tab, geo_tab = st.tabs(
        ["🗺️ Map", "📈 Trends", "🏷️ Crime types", "📍 Geography"]
    )
    with map_tab:
        map_view(f)
    with trends_tab:
        trends_view(f)
    with type_tab:
        type_view(f)
    with geo_tab:
        geo_view(f)


if __name__ == "__main__":
    main()
