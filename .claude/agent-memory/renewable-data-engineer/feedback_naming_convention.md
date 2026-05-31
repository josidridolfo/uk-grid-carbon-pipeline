---
name: naming-convention
description: Asset and model naming convention: <stage>_<source>__<desc> with double underscore before description segment
metadata:
  type: feedback
---

All Dagster assets, raw table names, and dbt models follow `<stage>_<source>__<desc>`:

- Single underscore between stage and source.
- **Double underscore** between source and description — this is the dbt community standard separator.
- `<stage>` values: `raw`, `stg`, `int`, `fact`, `dim`.
- `<source>` matches the dbt source `name:` in sources.yml AND the Dagster `group_name`. They must be identical.
- The Dagster asset Python function name is the Snowflake table name (the IO manager uses it directly). The `name:` in `models/sources.yml` must match exactly.

Examples: `raw_carbon_intensity__national`, `stg_neso__dno_polygons`, `dim_neso__dno_region`.

Mart models that genuinely join across multiple sources may omit the source segment (e.g. a future `fact_grid_state`). Single-source marts keep it (e.g. `fact_carbon_intensity_hourly`).

**Why:** User requested this convention explicitly. It's the standard dbt Labs community convention and is documented in CLAUDE.md under "Naming convention."

**How to apply:** Any new asset or dbt model file must conform. When reviewing stubs or future work, check both the Python function name and the sources.yml table name match with double-underscore.
