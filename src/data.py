"""Data access layer for the Chicago Crime dashboard.

Two access patterns, both cached:

1. **Map markers** -- a *bounded*, filtered, row-capped live query via sodapy.
   Never pulls more than ``config.MAX_MAP_POINTS`` rows so the browser stays
   responsive even against the full 2001-to-present dataset.

2. **Analytics** -- *server-side* SoQL aggregations (``count(*) ... GROUP BY``).
   The city's API does the counting; we only ever download small grouped
   result sets, so multi-year trends are cheap.

An optional on-disk Parquet snapshot (see ``scripts/refresh_data.py``) provides
an offline / hybrid path. If a snapshot exists it is used to answer the map
query without hitting the network; aggregations always prefer the live API for
freshness but transparently fall back to the snapshot if the network fails.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from sodapy import Socrata

from . import config

try:  # optional; .env is a convenience, not a requirement
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "snapshot.parquet"


# --- client -------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_client() -> Socrata:
    """A shared Socrata client. Token is optional (stricter rate limits without)."""
    token = os.getenv("SOCRATA_APP_TOKEN") or None
    return Socrata(config.SOCRATA_DOMAIN, token, timeout=60)


def has_app_token() -> bool:
    return bool(os.getenv("SOCRATA_APP_TOKEN"))


# --- SoQL where-clause builder ------------------------------------------------
def _quote_list(values) -> str:
    """Render a Python iterable as a SoQL ``IN (...)`` list, escaping quotes."""
    return ", ".join("'{}'".format(str(v).replace("'", "''")) for v in values)


def _build_where(
    start: date,
    end: date,
    crime_types: tuple[str, ...] = (),
    community_areas: tuple[int, ...] = (),
    arrest_only: bool = False,
    require_coords: bool = False,
) -> str:
    clauses = [
        f"date >= '{start.isoformat()}T00:00:00.000'",
        f"date <= '{end.isoformat()}T23:59:59.999'",
    ]
    if crime_types:
        clauses.append(f"primary_type in ({_quote_list(crime_types)})")
    if community_areas:
        clauses.append(f"community_area in ({_quote_list(community_areas)})")
    if arrest_only:
        clauses.append("arrest = true")
    if require_coords:
        clauses.append("latitude IS NOT NULL")
    return " AND ".join(clauses)


# --- map markers --------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner="Loading incidents for the map…")
def fetch_incidents(
    start: date,
    end: date,
    crime_types: tuple[str, ...] = (),
    community_areas: tuple[int, ...] = (),
    arrest_only: bool = False,
    limit: int = config.MAX_MAP_POINTS,
) -> pd.DataFrame:
    """Return up to ``limit`` individual incidents with coordinates, for the map.

    Ordered by date descending so, when the cap bites, you see the most recent
    incidents matching the filters.
    """
    client = get_client()
    where = _build_where(
        start, end, crime_types, community_areas, arrest_only, require_coords=True
    )
    records = client.get(
        config.DATASET_ID,
        select=", ".join(config.INCIDENT_COLUMNS),
        where=where,
        order="date DESC",
        limit=limit,
    )
    return _normalize_incidents(pd.DataFrame.from_records(records))


def _normalize_incidents(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=config.INCIDENT_COLUMNS)
    for col in ("latitude", "longitude"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["arrest"] = df.get("arrest").astype(str).str.lower().isin(["true", "1"])
    df["domestic"] = df.get("domestic").astype(str).str.lower().isin(["true", "1"])
    df = df.dropna(subset=["latitude", "longitude"])
    return df.reset_index(drop=True)


# --- aggregations (server-side) -----------------------------------------------
def _aggregate(select: str, group: str, where: str, order: str) -> pd.DataFrame:
    client = get_client()
    records = client.get(
        config.DATASET_ID,
        select=select,
        where=where,
        group=group,
        order=order,
        limit=50000,
    )
    return pd.DataFrame.from_records(records)


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_year(start, end, crime_types=(), community_areas=(), arrest_only=False):
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    df = _aggregate("year, count(id) as count", "year", where, "year")
    if df.empty:
        return df
    df["year"] = df["year"].astype(int)
    df["count"] = df["count"].astype(int)
    return df.sort_values("year")


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_month(start, end, crime_types=(), community_areas=(), arrest_only=False):
    """Crimes grouped by calendar month (1-12), aggregated across the range."""
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    df = _aggregate(
        "date_extract_m(date) as month, count(id) as count", "date_extract_m(date)",
        where, "date_extract_m(date)",
    )
    if df.empty:
        return df
    df["month"] = df["month"].astype(int)
    df["count"] = df["count"].astype(int)
    return df


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_hour(start, end, crime_types=(), community_areas=(), arrest_only=False):
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    df = _aggregate(
        "date_extract_hh(date) as hour, count(id) as count", "date_extract_hh(date)",
        where, "date_extract_hh(date)",
    )
    if df.empty:
        return df
    df["hour"] = df["hour"].astype(int)
    df["count"] = df["count"].astype(int)
    return df


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_dow(start, end, crime_types=(), community_areas=(), arrest_only=False):
    """Crimes by day of week. SoQL date_extract_dow: 0=Sunday .. 6=Saturday."""
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    df = _aggregate(
        "date_extract_dow(date) as dow, count(id) as count", "date_extract_dow(date)",
        where, "date_extract_dow(date)",
    )
    if df.empty:
        return df
    df["dow"] = df["dow"].astype(int)
    df["count"] = df["count"].astype(int)
    return df


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_type(start, end, crime_types=(), community_areas=(), arrest_only=False):
    """Count and arrest-count per primary type (two grouped queries, merged)."""
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    totals = _aggregate(
        "primary_type, count(id) as count", "primary_type", where, "count(id) DESC"
    )
    if totals.empty:
        return totals
    totals["count"] = totals["count"].astype(int)

    arrest_where = _build_where(
        start, end, crime_types, community_areas, arrest_only=True
    )
    arrests = _aggregate(
        "primary_type, count(id) as arrests", "primary_type", arrest_where, "primary_type"
    )
    if not arrests.empty:
        arrests["arrests"] = arrests["arrests"].astype(int)
        totals = totals.merge(arrests, on="primary_type", how="left")
    else:
        totals["arrests"] = 0
    totals["arrests"] = totals["arrests"].fillna(0).astype(int)
    totals["arrest_rate"] = (totals["arrests"] / totals["count"]).fillna(0)
    return totals.sort_values("count", ascending=False)


@st.cache_data(ttl=21600, show_spinner=False)
def agg_by_community_area(start, end, crime_types=(), community_areas=(), arrest_only=False):
    where = _build_where(start, end, crime_types, community_areas, arrest_only)
    df = _aggregate(
        "community_area, count(id) as count", "community_area", where, "count(id) DESC"
    )
    if df.empty:
        return df
    df = df.dropna(subset=["community_area"])
    df["count"] = df["count"].astype(int)
    df["area_name"] = df["community_area"].apply(config.community_area_name)
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def list_primary_types() -> list[str]:
    """Distinct primary types, for the filter multiselect."""
    try:
        df = _aggregate("primary_type", "primary_type", "primary_type IS NOT NULL",
                        "primary_type")
        return sorted(df["primary_type"].dropna().tolist())
    except Exception:
        return sorted(config.CRIME_TYPE_COLORS.keys())


# --- snapshot (offline / hybrid) ---------------------------------------------
def snapshot_exists() -> bool:
    return SNAPSHOT_PATH.exists()


def load_snapshot() -> pd.DataFrame:
    return pd.read_parquet(SNAPSHOT_PATH) if snapshot_exists() else pd.DataFrame()
