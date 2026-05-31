# Architecture

## Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  SOURCES                                    │
│   Carbon Intensity API   ─┐                                                 │
│   National Grid ESO      ─┤── public, no auth                               │
│   Met Office DataPoint   ─┘   (free API key)                                │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            INGESTION (Dagster assets)                       │
│   src/uk_grid/assets/                                                       │
│     carbon_intensity.py   ── raw_carbon_intensity__national (working)      │
│     grid_eso.py           ── raw_grid_eso__generation_by_fuel (stub)       │
│     met_office.py         ── raw_met_office__observations    (stub)        │
│     neso_geo.py           ── raw_neso__dno_polygons (static ref)           │
│                                                                             │
│   Materialised as Snowflake tables in UK_GRID.RAW.* via                    │
│   SnowflakePandasIOManager.                                                 │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TRANSFORMATION (dbt)                               │
│   dbt/models/                                                               │
│     staging/    (views; 1:1 with sources, cleaning + type casts)            │
│     intermediate/ (ephemeral; joins, business logic)                        │
│     marts/      (tables; the queryable end product)                         │
│                                                                             │
│   Tests: not_null, unique, accepted_range, accepted_values, source freshness│
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVING                                        │
│   src/uk_grid/dashboard/app.py  ── Streamlit, reads from MARTS schema (Snowflake) │
│   dbt docs (GitHub Pages) ── lineage + column-level documentation          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why each choice

### Dagster (over Airflow)

- **Asset-based model** fits analytics workloads where outputs (not just tasks) are the unit.
- **Software-defined assets** map cleanly to dbt models — dagster-dbt makes the integration
  one decorator deep.
- **Better local dev experience** — `dagster dev` boots a UI a recruiter can spin up
  in 30 seconds after cloning.

### dbt-core (over dbt Cloud, custom transformation)

- **Free, open-source, transparent.** Cloud is overkill for a portfolio project.
- **Tests + docs site** are the headline features. Without them this would just be SQL.

### Snowflake (over DuckDB / Postgres)

- **UK energy hiring market** — Octopus, Centrica, Ovo, OVO Kraken are Snowflake shops.
  Showing real Snowflake work (account params, role/warehouse use, micro-partitioning
  awareness) is more legible to recruiters than a DuckDB local file.
- **Native `GEOGRAPHY` type** with the full `ST_*` function family (`ST_Contains`,
  `ST_Within`, `ST_Centroid`, etc.) and built-in H3 cell functions. Enables spatial
  joins on DNO region polygons without an extension.
- **Production-grade RBAC** — separate roles for `LOADER`, `TRANSFORMER`, `REPORTER`;
  the profile demonstrates the pattern that scales to real teams.

### uv (over poetry, pip, conda)

- **Fastest installer.** Matters for CI.
- **Lockfile reproducibility** out of the box.
- **Pre-installed in modern dev environments** (DSPy, Anthropic, etc. use it).

## Trade-offs and limitations

- **Snowflake credentials required.** Clone-and-run is no longer a 30-second affair —
  readers need a Snowflake trial account and a populated `.env`. The trade-off is
  intentional: this is the warehouse the target employer market uses.
- **No incremental ingestion yet.** First commit pulls the trailing 24 hours every run.
  Add a Dagster partition definition + `dbt incremental` materialisation for backfills.
- **Three sources, only one ingested.** ESO and Met Office are stubs in this commit.

## Geo layer

The DNO polygons come from the NESO data portal in EPSG:27700 (British National Grid).
Snowflake `GEOGRAPHY` requires EPSG:4326, so the `raw_neso__dno_polygons` Dagster asset
reprojects with shapely+pyproj during ingestion and writes WKT. This puts the projection
step in the observable asset lineage rather than in an opaque pre-processing script.

The Carbon Intensity API uses numeric region IDs 1-14 and three region names that differ
slightly from the official GeoJSON names. `seeds/dno_region_mapping.csv` is the explicit
14-row cross-walk. `dim_dno_region` joins the staged polygon to the seed on `geojson_id`,
exposing `api_regionid` as the canonical surrogate key for all downstream joins to Carbon
Intensity data.

Future spatial work (weather stations to region, charge points to region) joins to
`dim_dno_region.polygon` via `ST_CONTAINS` / `ST_WITHIN`.

## Data lineage

Once dbt has been built, browse the lineage at `target/index.html`:

```bash
make dbt-docs
# open http://localhost:8080
```

The published version (after CI merges to main) lives at
`https://josidridolfo.github.io/uk-grid-carbon-pipeline/`.
