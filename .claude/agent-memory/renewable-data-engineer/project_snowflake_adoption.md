---
name: snowflake-adoption
description: DuckDB dropped; Snowflake is the sole warehouse. CI runs dbt parse only — no live warehouse connection in PR validation.
metadata:
  type: project
---

DuckDB has been removed entirely. Snowflake is the only warehouse target.

**Why:** UK energy hiring market (Octopus, Centrica, OVO are Snowflake shops); native GEOGRAPHY type enables the geo layer; production-grade RBAC/clustering demonstrates real-world engineering.

**Key details:**
- `dagster-snowflake`, `dagster-snowflake-pandas`, `dbt-snowflake` replace all DuckDB packages.
- `shapely>=2.0` and `pyproj>=3.6` added for EPSG:27700→4326 reprojection.
- `SnowflakePandasIOManager` in `src/uk_grid/resources.py`. Auth: key-pair if `SNOWFLAKE_PRIVATE_KEY_PATH` is set, else password.
- Single flat schema `RAW` for all raw assets (`UK_GRID.RAW.*`). Controlled by `SNOWFLAKE_SCHEMA` env var (default `RAW`). No per-source schema overrides — source identity encoded in table name.
- dbt models land in `ANALYTICS_STAGING.*` and `ANALYTICS_MARTS.*`. Base controlled by `SNOWFLAKE_DBT_SCHEMA` env var (default `ANALYTICS`). Per-layer suffix appended by `dbt_project.yml` `+schema` config.
- CI runs `dbt parse --project-dir dbt --profiles-dir dbt` only — no warehouse connection needed for PR validation. CI copies `dbt/profiles.yml.example` to `~/.dbt/profiles.yml`.
- A separate `nightly-build.yml` workflow (not yet created) should run the full `dbt build` with Snowflake secrets.
- Snowflake database name convention: `UK_GRID` (uppercase, per Snowflake convention).

**How to apply:** Never suggest DuckDB targets or DuckDB-specific SQL in this repo. Never suggest per-source RAW_* schemas — all raw assets go to RAW. Always pass `--project-dir dbt --profiles-dir dbt` to dbt commands. Warn if any DuckDB-specific syntax creeps in.
