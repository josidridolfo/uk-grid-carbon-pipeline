---
name: portfolio-project-state
description: Current state of the uk-grid-carbon-pipeline portfolio project and recommended direction
metadata:
  type: project
---

**Project:** UK Grid Carbon Intensity Pipeline at /Users/josid/Documents/PROJECTS/uk-grid-carbon-pipeline

**Stack (as of 2026-05-31):**
- Dagster + dbt + Snowflake (native GEOGRAPHY type). Snowflake RBAC pattern: LOADER/TRANSFORMER/REPORTER roles bootstrapped via `infra/snowflake_init.sql`.
- `src/uk_grid/` layout, `dbt/` consolidated, CI green on `dbt parse` (credential-free).
- Credentials in place but asset graph not yet run end-to-end against Snowflake.

**What's working:**
- `raw_carbon_intensity__national` (national half-hourly actuals from Carbon Intensity API) — one live asset.
- Geo layer: NESO DNO polygons reprojected EPSG:27700→4326 in a Dagster asset; `dim_dno_region` mart joins via `dbt/seeds/dno_region_mapping.csv` (14-row seed resolving Carbon Intensity API regional IDs to official DNO licence area GeoJSON).
- CI via GitHub Actions (dbt parse on every PR).

**Stubs not yet implemented:**
- `raw_carbon_intensity__regional` — Carbon Intensity API /regional endpoint
- `raw_grid_eso__generation_by_fuel` — NESO Historic Generation Mix
- `raw_met_office__observations` — Met Office MIDAS/DataPoint
- Octopus Agile API (not yet wired)
- No public dashboard yet. No blog posts published.

**Recommended sequencing (updated 2026-05-31):**

1. **Next 4 weeks (by mid-July 2026):** Complete `raw_carbon_intensity__regional`, wire to `dim_dno_region`, render a DNO-region choropleth ("lowest carbon intensity region in last 7 days") on Streamlit Cloud. Publish LinkedIn post with one-line finding and live URL. This is the highest-leverage move: completes the geo layer already half-built, produces a quotable artefact, and is legible to hiring managers before August slowdown.

2. **July–September 2026:** Add Octopus Agile tariff pricing + counterfactual savings model ("cheapest AND greenest hour to charge an EV by region"). This adds analytical depth but is not publishable standalone — needs the regional layer done first.

3. **September–October 2026:** NESO generation mix, Met Office weather correlation, polish dashboard.

4. **October–November 2026:** Application window. Target: Octopus Energy data platform team, NESO Data and Digital group, Energy Systems Catapult, OVO/Kraken.

**Why:** Agile tariff integration was originally recommended as first next step, but revised: it produces no standalone quotable artefact until the counterfactual savings model is also complete (6-8 weeks). Regional map ships faster and demonstrates the most domain-specific work (DNO geo reconciliation) that a hiring manager can verify with a single screenshot.

**Hireability signal the geo layer sends:** The 14-row DNO reconciliation seed is the most differentiating work in the repo — it shows the builder has read actual UK energy data, not just followed a tutorial. Currently invisible to anyone not reading the SQL; needs to be surfaced via a public artefact.

**Timing note:** UK energy sector hiring slows in August. Post the regional map artefact by mid-July 2026. Applications target October–November 2026.

**Why:** Sequencing revised to front-load the regional map because it (a) completes half-built work, (b) is achievable in 4 weeks, and (c) produces a visa-justifiable public artefact before the August hiring slowdown.
