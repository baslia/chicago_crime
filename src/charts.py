"""Visualization helpers: the folium crime map and the Plotly analytics charts."""

from __future__ import annotations

import calendar

import folium
import pandas as pd
import plotly.express as px
from folium.plugins import MarkerCluster

from . import config

DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # SoQL dow: 0=Sun


# --- map ----------------------------------------------------------------------
def build_map(df: pd.DataFrame) -> folium.Map:
    """A folium map of incidents, colored by primary type and clustered."""
    m = folium.Map(
        location=list(config.CHICAGO_CENTER),
        zoom_start=config.DEFAULT_ZOOM,
        tiles="CartoDB positron",
    )
    if df.empty:
        return m

    cluster = MarkerCluster(name="Incidents").add_to(m)
    for row in df.itertuples(index=False):
        color = config.color_for(getattr(row, "primary_type", ""))
        when = getattr(row, "date", None)
        when_str = when.strftime("%Y-%m-%d %H:%M") if pd.notna(when) else "unknown"
        popup = folium.Popup(
            f"<b>{getattr(row, 'primary_type', 'Unknown')}</b><br>"
            f"{getattr(row, 'description', '') or ''}<br>"
            f"<i>{getattr(row, 'location_description', '') or ''}</i><br>"
            f"{when_str}<br>"
            f"Arrest: {'Yes' if getattr(row, 'arrest', False) else 'No'}",
            max_width=280,
        )
        folium.CircleMarker(
            location=(row.latitude, row.longitude),
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=1,
            popup=popup,
            tooltip=getattr(row, "primary_type", None),
        ).add_to(cluster)
    return m


def build_choropleth(area_df: pd.DataFrame, geojson: dict) -> folium.Map:
    """Shade the 77 community areas by crime count, with a hover tooltip."""
    m = folium.Map(
        location=list(config.CHICAGO_CENTER),
        zoom_start=config.DEFAULT_ZOOM,
        tiles="CartoDB positron",
    )
    if area_df.empty:
        return m

    # Keyed on the string area code present in both the GeoJSON (`area_numbe`)
    # and the aggregation (`community_area`).
    counts = area_df.copy()
    counts["community_area"] = counts["community_area"].astype(str)

    folium.Choropleth(
        geo_data=geojson,
        data=counts,
        columns=["community_area", "count"],
        key_on="feature.properties.area_numbe",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.3,
        nan_fill_color="#f0f0f0",
        legend_name="Crimes in selected range",
        name="Crime density",
    ).add_to(m)

    # A transparent GeoJson layer on top to carry an interactive tooltip.
    lookup = dict(zip(counts["community_area"], counts["count"]))
    for feat in geojson["features"]:
        code = str(feat["properties"].get("area_numbe"))
        feat["properties"]["crimes"] = int(lookup.get(code, 0))
        feat["properties"]["name"] = feat["properties"].get("community", "").title()
    folium.GeoJson(
        geojson,
        style_function=lambda _f: {"fillOpacity": 0, "color": "transparent", "weight": 0},
        highlight_function=lambda _f: {"weight": 2, "color": "#333", "fillOpacity": 0.1},
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "crimes"],
            aliases=["Community area:", "Crimes:"],
            localize=True,
        ),
        name="Hover",
    ).add_to(m)
    return m


def type_legend(df: pd.DataFrame) -> list[tuple[str, str]]:
    """(type, color) pairs present in the current map data, for a legend."""
    if df.empty:
        return []
    types = df["primary_type"].dropna().unique().tolist()
    return [(t, config.color_for(t)) for t in sorted(types)]


# --- analytics ----------------------------------------------------------------
def chart_by_year(df: pd.DataFrame):
    fig = px.bar(df, x="year", y="count", labels={"count": "Crimes", "year": "Year"})
    fig.update_traces(marker_color="#4e79a7")
    return _style(fig, "Crimes per year")


def chart_by_month(df: pd.DataFrame):
    d = df.copy()
    d["label"] = d["month"].apply(lambda m: calendar.month_abbr[m])
    d = d.sort_values("month")
    fig = px.line(d, x="label", y="count", markers=True,
                  labels={"count": "Crimes", "label": "Month"})
    fig.update_traces(line_color="#e15759")
    return _style(fig, "Seasonality (by month)")


def chart_by_hour(df: pd.DataFrame):
    d = df.sort_values("hour")
    fig = px.bar(d, x="hour", y="count", labels={"count": "Crimes", "hour": "Hour of day"})
    fig.update_traces(marker_color="#59a14f")
    fig.update_xaxes(dtick=2)
    return _style(fig, "Time of day")


def chart_by_dow(df: pd.DataFrame):
    d = df.copy()
    d["label"] = d["dow"].apply(lambda x: DOW_LABELS[x])
    d = d.sort_values("dow")
    fig = px.bar(d, x="label", y="count", labels={"count": "Crimes", "label": "Day"})
    fig.update_traces(marker_color="#f28e2b")
    return _style(fig, "Day of week")


def chart_by_type(df: pd.DataFrame, top_n: int = 20):
    d = df.head(top_n).iloc[::-1]
    fig = px.bar(
        d, x="count", y="primary_type", orientation="h",
        color="primary_type",
        color_discrete_map={t: config.color_for(t) for t in d["primary_type"]},
        labels={"count": "Crimes", "primary_type": ""},
        hover_data={"arrest_rate": ":.1%"},
    )
    fig.update_layout(showlegend=False)
    return _style(fig, f"Top {min(top_n, len(df))} crime types")


def chart_arrest_rate_by_type(df: pd.DataFrame, top_n: int = 15):
    d = df.head(top_n).copy()
    d = d.sort_values("arrest_rate", ascending=True)
    fig = px.bar(
        d, x="arrest_rate", y="primary_type", orientation="h",
        labels={"arrest_rate": "Arrest rate", "primary_type": ""},
    )
    fig.update_traces(marker_color="#b07aa1")
    fig.update_xaxes(tickformat=".0%")
    return _style(fig, "Arrest rate by type")


def chart_by_area(df: pd.DataFrame, top_n: int = 20):
    d = df.head(top_n).iloc[::-1]
    fig = px.bar(
        d, x="count", y="area_name", orientation="h",
        labels={"count": "Crimes", "area_name": ""},
    )
    fig.update_traces(marker_color="#76b7b2")
    return _style(fig, f"Top {min(top_n, len(df))} community areas")


def _style(fig, title: str):
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=40, b=10),
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
