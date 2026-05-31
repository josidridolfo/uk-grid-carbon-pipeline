# Agent Memory Index

- [Naming convention](feedback_naming_convention.md) — `<stage>_<source>__<desc>` with double-underscore separator; Dagster fn name = Snowflake table name
- [Warehouse choice: Snowflake](project_snowflake_adoption.md) — DuckDB dropped; single RAW schema; dbt lands in ANALYTICS_STAGING/ANALYTICS_MARTS; CI credential-free
- [Repo structure](project_repo_structure.md) — src/uk_grid/ for Python, dbt/ for all dbt artefacts; always pass --project-dir dbt --profiles-dir dbt
- [Geo layer design](project_geo_layer.md) — DNO polygons asset, EPSG:27700→4326 reprojection in Dagster, dim_dno_region mart (implemented; 14-row row-count test)
