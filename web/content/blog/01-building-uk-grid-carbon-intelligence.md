---
title: "Building a UK grid carbon intelligence platform — Phase 1: foundations"
slug: building-uk-grid-carbon-intelligence-phase-1
published_at: 2026-05-31
description: "A walkthrough of how the foundations of energy-project.ridol.fo were built — from a Snowflake bootstrap script to a Dagster + dbt data pipeline that lands UK Carbon Intensity API data into a queryable analytics layer."
tags: [infrastructure, dbt, dagster, snowflake, methodology]
---

## What is this site?

energy-project.ridol.fo is a UK grid carbon intelligence platform: a live dashboard and blog that tracks when the UK electricity grid is greenest, broken down by the 14 DNO licence regions that map to real supply zones. It runs on a DigitalOcean droplet, behind a Caddy reverse proxy, with every production deploy triggered automatically from a GitHub Actions workflow on push to `main`. The site is read-only at the Django layer — no user accounts, no writes — which keeps the attack surface minimal and the infrastructure boring in the best possible way.

The pipeline behind it is not a toy. It ingests real data from the [Carbon Intensity API](https://carbonintensity.org.uk/) (maintained by National Grid ESO and EDF Europe), stores it in Snowflake, transforms it through a dbt dimensional model, and serves it via a Django + htmx frontend. This post covers Phase 1: everything it took to get from an empty repo to a fully tested data foundation.

---

## The data foundation

The Carbon Intensity API exposes two endpoints that matter here:

- **National intensity** — a single `intensity.actual` and `intensity.forecast` value for GB as a whole, at half-hourly granularity, with a `generationmix` breakdown showing the share from biomass, coal, gas, hydro, imports, nuclear, other, solar, and wind.
- **Regional intensity** — the same half-hourly data, but broken out across 14 regions identified by a numeric `regionid` (1–14) and a `shortname`. This is where the interesting spatial analysis lives.

Alongside the API data, the pipeline ingests two geographic datasets published by NESO (National Energy System Operator) under open licence:

- **DNO licence polygons** — a GeoJSON file containing the exact boundary polygons for each of the 14 Distribution Network Operator licence areas. These are the shapes that appear on the choropleth map.
- **A reconciliation seed** — more on this below, but the short version is that the API's region names and the GeoJSON's feature names do not match, and numeric IDs are on completely different scales (1–14 vs 10–23). An explicit `dno_region_mapping.csv` seed is the single source of truth that joins them cleanly.

The DNO polygons are stored with a `GEOGRAPHY` column in Snowflake, enabling spatial joins against any point or polygon geometry without exporting to a GIS tool.

---

## The architecture

The data flows through four layers:

```
Carbon Intensity API  ──►  Dagster asset  ──►  Snowflake RAW.*
NESO GeoJSON          ──►  Dagster asset  ──►  Snowflake RAW.*
                                                      │
                                              dbt build
                                                      │
                                    ANALYTICS_STAGING.*  (cleaned, typed)
                                                      │
                                      ANALYTICS_MARTS.*  (dimensional)
                                                      │
                                      Django (REPORTER role, read-only)
```

**Dagster** runs as a containerised service. Each asset maps to one API endpoint or file fetch. Assets are partitioned daily — re-running a partition re-ingests that day's data without duplicating rows, because the landing tables use `MERGE` semantics keyed on `(settlement_date, settlement_period, regionid)`.

**dbt** sits downstream of Snowflake `RAW.*`. The staging layer applies type coercions, renames columns to snake_case, and adds `_loaded_at` audit columns. The marts layer builds:

- `dim_date` — calendar dimension with ISO week, quarter, and DST offset flag (important for UK grid analysis, where winter demand peaks differ from summer).
- `dim_dno_region` — one row per DNO licence region, joining the reconciliation seed to the GeoJSON polygons. The `GEOGRAPHY` column lives here.
- `fact_regional_carbon_intensity` — one row per (settlement_date, settlement_period, api_regionid), keyed on the API's `regionid` as the surrogate key. Carbon intensity in gCO₂/kWh, generation mix percentages, and foreign keys to `dim_dno_region` and `dim_date`.
- `fact_national_carbon_intensity` — the GB-level equivalent, with `generationmix` percentages denormalised as columns.

The Django app connects as the `REPORTER` role, which has `SELECT` on `ANALYTICS_MARTS.*` only. It cannot touch `RAW.*`, cannot run `MERGE`, and cannot access the dbt staging schema. This separation is enforced at the Snowflake role level, not just convention.

---

## The TDD discipline

Every layer was built test-first. The discipline matters because energy data has a dozen ways to go wrong silently: the API returns a 200 but with empty `data`, intensity values of `null` during generation outages, region shortnames that don't match historical values, BST/UTC confusion in settlement period calculations.

**Pure parse functions** are the first defence. The ingestion code separates I/O (fetching the API) from parsing (turning the JSON response into typed rows). The parse function has this signature:

```python
def _parse_intensity_rows(
    response_json: dict,
    fetched_at: datetime,
) -> list[IntensityRow]:
    ...
```

That function is tested in isolation — no network, no Snowflake, no mocking of HTTP clients. Pass it a dict that looks like the API response and assert on the returned dataclass fields. Edge cases covered: missing `intensity.actual` (returns `None`, does not raise), empty `data` list (returns `[]`), `generationmix` with an unknown fuel type (logs a warning, preserves the row).

**dbt tests** cover every mart model. The test suite runs 88 tests across `not_null`, `unique`, `accepted_values`, and `relationships` constraints. A `relationships` test between `fact_regional_carbon_intensity.dno_region_id` and `dim_dno_region.dno_region_id` is the canary: if the reconciliation seed is wrong, this test fails at `dbt build` time, not at query time in production.

**Frontend components** are tested with Django's `render_to_string` — no HTTP request needed, no database required. The 10 Tailwind components (hero, card, badge, nav_link, metric_tile, map_container, loading_fragment, error_fragment, theme_toggle, base_layout) each have 5–9 tests covering required context variables, ARIA attributes, and data-testid hooks for future Playwright tests.

A snapshot from the dbt test run:

```
Running with dbt=1.9.3
Found 12 models, 88 tests, 3 seeds, 4 sources

Completed successfully
Done. PASS=88 WARN=0 ERROR=0 SKIP=0 TOTAL=88
```

---

## What's next

Phase 2 wired the national carbon intensity chart — a live Plotly time series updated every 30 minutes via htmx polling. Phase 5 will add the regional choropleth: a Plotly choropleth_mapbox layer driven by `dim_dno_region.GEOGRAPHY` polygons and coloured by the latest `fact_regional_carbon_intensity` value.

The next substantive analysis post will cover the DNO region reconciliation problem in detail — why the API's `regionid` 1–14 and the GeoJSON's `ID` 10–23 are on completely different scales, and what three name mismatches look like in practice. That post has a direct engineering payoff: it explains why `dno_region_mapping.csv` exists and what breaks if you remove it.

Regional smart-charging analysis is the long-term goal. If you're scheduling EV charging in South West England versus North Scotland, the optimal window differs by two to four hours on most days. The pipeline has everything needed to quantify that — it's a matter of building the right query.
