# UK Grid Carbon Intensity Pipeline

> When is the UK electricity grid greenest, and why?

A production-grade data pipeline that ingests UK electricity grid data, weather observations,
and carbon-intensity forecasts, transforms them through dbt into a dimensional model, and
serves analytics-ready marts you can query, dashboard, or build forecasts on.

Built with [Dagster](https://dagster.io) + [dbt](https://www.getdbt.com) on
[DuckDB](https://duckdb.org), with all data sourced from free, public UK APIs.

## What this is, in one diagram

```
            ┌─────────────────────────┐
            │   Dagster (orchestration)│
            └─────────────┬────────────┘
                          │
   ┌──────────────────────┼──────────────────────┐
   ▼                      ▼                       ▼
Carbon Intensity     National Grid ESO       Met Office
   API                Open Data API         DataPoint API
   │                      │                      │
   └──────────────┬───────┴──────────────┬───────┘
                  │   raw layer (DuckDB) │
                  ▼                      ▼
         ┌──────────────────────────────────────┐
         │  dbt: staging → intermediate → marts │
         └──────────────────┬───────────────────┘
                            ▼
            ┌────────────────────────────────┐
            │  Streamlit dashboard +         │
            │  dbt docs site (GitHub Pages)  │
            └────────────────────────────────┘
```

## Why it exists

Three audiences I'm building this for, in priority order:

1. **Recruiters in UK energy / climate-tech / utilities** — to demonstrate hands-on
   modern data engineering on a problem they actually care about.
2. **Myself** — I want to know, viscerally, when the UK grid is greenest. I'll use
   this dataset to time my own household electricity usage.
3. **The data engineering community** — a fully open, fully reproducible reference
   implementation for the Dagster + dbt + DuckDB stack on real public data.

## What it answers (analytical marts)

- `mart_carbon_intensity_hourly` — half-hour resolution carbon intensity for every
  GB region, joined to fuel mix and demand.
- `mart_weather_vs_carbon` — correlations between weather (wind, irradiance,
  temperature) and grid carbon intensity, by region and time-of-day.
- `mart_greenest_hour_recommendations` — for any region and 24-hour forward window,
  the optimal 2-hour slot for high-load activities.

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/josidridolfo/uk-grid-carbon-pipeline.git
cd uk-grid-carbon-pipeline
uv sync                       # creates .venv, installs everything

# 2. Configure (Met Office DataPoint API key — free, optional)
cp .env.example .env
# edit .env, set MET_OFFICE_API_KEY if you want weather data

# 3. Initialise dbt profile (one-time)
cp profiles.yml.example ~/.dbt/profiles.yml

# 4. Spin up Dagster locally
uv run dagster dev
# UI at http://localhost:3000 — click "Materialize all" to populate raw layer

# 5. Run dbt
uv run dbt build              # staging → intermediate → marts, with tests

# 6. View the lineage docs
uv run dbt docs generate && uv run dbt docs serve
# UI at http://localhost:8080
```

## Stack

| Layer            | Tool                                                              |
| ---------------- | ----------------------------------------------------------------- |
| Orchestration    | Dagster (asset-graph)                                             |
| Transformation   | dbt-core 1.x                                                      |
| Warehouse        | DuckDB (file-based; swap for Snowflake / Postgres via dbt profile) |
| Sources          | Carbon Intensity API, National Grid ESO Open Data, Met Office     |
| Language         | Python 3.12 (with `uv` for env mgmt)                              |
| Dashboard        | Streamlit                                                         |
| CI               | GitHub Actions (`dbt build` + `pytest` on every PR)               |

## Engineering decisions worth noting

- **Incremental dbt models** with `unique_key` + `merge` strategies for time-series sources.
  Carbon Intensity API is half-hourly; running this every 15 minutes only writes new rows.
- **Dagster asset partitions** for daily backfills — pull historical data without rewriting
  pipeline code.
- **Source freshness checks** in dbt catch upstream API outages before downstream marts
  go stale.
- **Bad-row quarantine** for rows that fail schema checks — `mart_*_invalid` tables capture
  them so I can investigate, not silently drop.
- **Zero credentials in the repo.** Carbon Intensity API requires no auth. Met Office is via
  a local-only `.env` file.

## Repo layout

```
uk-grid-carbon-pipeline/
├── uk_grid/                 # Dagster definitions and asset code
│   ├── assets/              # one file per source domain
│   ├── resources.py         # DuckDB I/O manager, HTTP client
│   └── definitions.py       # the Dagster Definitions object
├── models/                  # dbt models
│   ├── staging/             # 1:1 with sources, cleaning only
│   ├── intermediate/        # business logic, joins
│   └── marts/               # the queryable end product
├── seeds/                   # static reference data (region codes, fuel-type lookups)
├── tests/                   # generic + custom dbt tests, pytest for Python code
├── macros/                  # reusable dbt macros (date spine, etc.)
├── dashboard/               # Streamlit app reading the marts
├── docs/                    # architecture, ADRs, notes
├── data/                    # DuckDB file (gitignored)
├── .github/workflows/       # CI
├── dbt_project.yml
├── profiles.yml.example
├── pyproject.toml
└── README.md
```

## Roadmap

- [x] Skeleton (this commit): one Carbon Intensity asset, one dbt staging model,
      one mart model, working DuckDB target, CI workflow.
- [ ] National Grid ESO generation-mix ingestion.
- [ ] Met Office weather ingestion (forecast + observations).
- [ ] Regional dim model (GB DNO regions).
- [ ] Weather × carbon-intensity correlation mart.
- [ ] Streamlit dashboard with three views: current intensity, weather correlation,
      "best hour to do laundry."
- [ ] dbt docs auto-published to GitHub Pages.
- [ ] Dagster sensor for fresh-data trigger.
- [ ] Streamlit dashboard hosted on Streamlit Community Cloud.

## License

MIT. See `LICENSE`.

## Acknowledgements

- [National Grid ESO](https://www.nationalgrideso.com/data-portal) for open data publication.
- [Carbon Intensity API](https://carbonintensity.org.uk/) maintained by National Grid ESO and
  the Environmental Defense Fund Europe.
- [Met Office DataPoint](https://www.metoffice.gov.uk/services/data) for the weather API.
