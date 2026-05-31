# UK Grid Carbon Intensity Pipeline

> When is the UK electricity grid greenest, and why?

A production-grade data pipeline that ingests UK electricity grid data, weather observations,
and carbon-intensity forecasts, transforms them through dbt into a dimensional model, and
serves analytics-ready marts you can query, dashboard, or build forecasts on.

Built with [Dagster](https://dagster.io) + [dbt](https://www.getdbt.com) on
[Snowflake](https://www.snowflake.com), with all data sourced from free, public UK APIs.

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
                  │  raw layer (Snowflake) │
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

# 2. Configure your Snowflake + Met Office credentials
cp .env.example .env
# edit .env — set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
# and (optionally) MET_OFFICE_API_KEY

# 3. Bootstrap Snowflake — warehouse, database, schemas, role hierarchy, grants
make snowflake-init            # idempotent; safe to re-run
# Alternative: paste infra/snowflake_init.sql into the Snowsight UI

# 4. Initialise the dbt profile (one-time)
cp dbt/profiles.yml.example dbt/profiles.yml
# profile uses env_var() substitutions — no editing needed if .env is set

# 5. Spin up Dagster locally
uv run dagster dev
# UI at http://localhost:3000 — click "Materialize all" to populate raw layer

# 6. Run dbt
make dbt-deps                  # install dbt packages (one-time)
make dbt-build                 # staging → intermediate → marts, with tests

# 7. View the lineage docs
make dbt-docs                  # generates and serves at http://localhost:8080
```

## Stack

| Layer            | Tool                                                              |
| ---------------- | ----------------------------------------------------------------- |
| Orchestration    | Dagster (asset-graph)                                             |
| Transformation   | dbt-core 1.x                                                      |
| Warehouse        | Snowflake (with native GEOGRAPHY for geo joins)                    |
| Sources          | Carbon Intensity API, National Grid ESO Open Data, Met Office     |
| Language         | Python 3.12 (with `uv` for env mgmt)                              |
| Dashboard        | Streamlit                                                         |
| CI               | GitHub Actions (ruff + pytest + dbt parse on every PR; nightly dbt build with Snowflake secrets) |

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
- **Snowflake GEOGRAPHY for spatial joins** — DNO region polygons reprojected from EPSG:27700
  to EPSG:4326 during ingestion, stored as native `GEOGRAPHY` for `ST_CONTAINS`/`ST_WITHIN`
  joins to weather stations, charge points, and time-series.
- **Explicit reconciliation seed** — the Carbon Intensity API and the NESO GeoJSON disagree
  on region IDs and three region names; `dbt/seeds/dno_region_mapping.csv` is the single
  source of truth for the cross-walk, avoiding brittle string joins.

## Repo layout

```
uk-grid-carbon-pipeline/
├── src/
│   └── uk_grid/             # Dagster definitions and asset code
│       ├── assets/          # one file per source domain
│       ├── dashboard/       # Streamlit app reading the marts
│       ├── resources.py     # Snowflake I/O manager + settings
│       └── definitions.py   # the Dagster Definitions object
├── dbt/                     # all dbt artefacts
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml.example
│   ├── models/              # staging → intermediate → marts
│   ├── seeds/               # region mappings + reference seeds
│   ├── macros/              # reusable dbt macros (date spine, etc.)
│   └── tests/               # dbt singular tests
├── tests/                   # Python (pytest) tests
├── data/                    # reference geo data
├── docs/                    # architecture, ADRs, notes
├── infra/                   # Snowflake bootstrap script
├── .github/workflows/       # CI
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

## Data attribution

- **Carbon Intensity API** — National Grid ESO and Environmental Defense Fund Europe.
  See https://carbonintensity.org.uk/.
- **NESO DNO Licence Areas** — *Supported by National Energy SO Open Data*.
  Published under the [NESO Open Data Licence](https://www.neso.energy/data-portal/ngeso-open-licence).
- **Met Office DataPoint** — Crown copyright, Met Office.

## License

MIT. See `LICENSE`.

## Acknowledgements

- [National Grid ESO](https://www.nationalgrideso.com/data-portal) for open data publication.
- [Carbon Intensity API](https://carbonintensity.org.uk/) maintained by National Grid ESO and
  the Environmental Defense Fund Europe.
- [Met Office DataPoint](https://www.metoffice.gov.uk/services/data) for the weather API.
