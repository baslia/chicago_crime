# 🐕 Chicago Crime Dashboard

An open-source, interactive dashboard exploring crime in Chicago using the
City of Chicago's open data. Built with [Streamlit](https://streamlit.io),
[folium](https://python-visualization.github.io/folium/), and
[Plotly](https://plotly.com/python/), reading live from the
[Socrata SODA API](https://dev.socrata.com/) via
[sodapy](https://github.com/afeld/sodapy).

**Data source:** [Crimes - 2001 to Present](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)
(dataset `ijzp-q8t2`, ~8M records).

## Features

- 🗺️ **Interactive map** — individual incidents as clustered markers, colored by
  crime type, with a details popup on click.
- 📈 **Trends** — crimes by year, month (seasonality), day of week, and hour.
- 🏷️ **Crime types** — ranked breakdown with per-type arrest rates.
- 📍 **Geography** — totals by Chicago's 77 community areas.
- 🎛️ **Filters** — date range (back to 2001), crime type, community area,
  arrests-only.
- 📊 **KPI cards** — total crimes, arrest rate, most common type, year-over-year change.

## How it scales to the full dataset

Plotting millions of markers would crash a browser, so:

- **Analytics** use *server-side SoQL aggregations* (`SELECT count(*) ... GROUP BY`).
  Chicago's API does the counting; only small grouped results are downloaded, so
  multi-year queries stay fast.
- **The map** runs a *bounded* query capped at `MAX_MAP_POINTS` (default 5,000),
  showing the most recent incidents matching your filters.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

### Optional: app token (higher rate limits)

The dashboard works without a token, just with stricter API rate limits.
For more headroom, grab a free
[Socrata app token](https://data.cityofchicago.org/profile/edit/developer_settings):

```bash
cp .env.example .env
# edit .env and set SOCRATA_APP_TOKEN=...
```

### Optional: local snapshot (offline / hybrid)

Cache a recent window of incidents to Parquet for offline map queries:

```bash
python -m scripts.refresh_data --days 365
```

## Project layout

```
app.py                  Streamlit UI: filters, KPIs, map, analytics tabs
src/config.py           Dataset ID, crime-type colors, 77 community areas
src/data.py             sodapy client, cached live queries + SoQL aggregations
src/charts.py           folium map + Plotly charts
scripts/refresh_data.py Build the local Parquet snapshot
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at `app.py`.
3. (Optional) add `SOCRATA_APP_TOKEN` under the app's **Secrets**.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. This is a community project; the crime data is provided
by the City of Chicago and is subject to their
[terms of use](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html).
Data reflects reported incidents and carries known caveats (reporting lag,
reclassification, and preliminary records); it should not be treated as a
definitive account of crime.
