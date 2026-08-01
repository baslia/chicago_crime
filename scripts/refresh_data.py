"""Build a local Parquet snapshot for the offline / hybrid data path.

Pulls incidents (with coordinates) for a recent window into
``data/snapshot.parquet`` so the dashboard can answer map queries without
hitting the network. Analytics still prefer the live SoQL API.

Usage:
    python -m scripts.refresh_data --days 365
    python -m scripts.refresh_data --start 2023-01-01 --end 2023-12-31
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

import pandas as pd
from sodapy import Socrata

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src import config
from src.data import SNAPSHOT_PATH, _normalize_incidents


def refresh(start: date, end: date, page_size: int = 50000) -> pd.DataFrame:
    token = os.getenv("SOCRATA_APP_TOKEN") or None
    client = Socrata(config.SOCRATA_DOMAIN, token, timeout=120)
    where = (
        f"date >= '{start.isoformat()}T00:00:00.000' AND "
        f"date <= '{end.isoformat()}T23:59:59.999' AND latitude IS NOT NULL"
    )
    rows, offset = [], 0
    while True:
        batch = client.get(
            config.DATASET_ID,
            select=", ".join(config.INCIDENT_COLUMNS),
            where=where,
            order="date DESC",
            limit=page_size,
            offset=offset,
        )
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        print(f"  fetched {len(rows):,} rows…")

    df = _normalize_incidents(pd.DataFrame.from_records(rows))
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SNAPSHOT_PATH, index=False)
    print(f"Wrote {len(df):,} rows to {SNAPSHOT_PATH}")
    return df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=365, help="Trailing window size.")
    p.add_argument("--start", type=str, help="ISO date, overrides --days.")
    p.add_argument("--end", type=str, help="ISO date, defaults to today.")
    args = p.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = (
        date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days)
    )
    print(f"Refreshing snapshot: {start} → {end}")
    refresh(start, end)


if __name__ == "__main__":
    main()
