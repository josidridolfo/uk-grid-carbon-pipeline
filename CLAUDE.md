# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python env and dependencies are managed by `uv`. dbt commands need a `profiles.yml` — copy `dbt/profiles.yml.example` to `~/.dbt/profiles.yml` and fill in your Snowflake credentials, then pass `--project-dir dbt --profiles-dir dbt` to all dbt commands (the `Makefile` targets do this automatically).

| Task | Command |
| --- | --- |
| Install deps | `uv sync` (or `make install`) |
| Start Dagster UI on :3000 | `uv run dagster dev` (or `make dev`) |
| Materialise one asset (CLI) | `uv run dagster asset materialize --select raw_carbon_intensity__national -m uk_grid.definitions` |
| Run all dbt models + tests | `uv run dbt build --project-dir dbt --profiles-dir dbt` (or `make dbt-build`) |
| Run only dbt tests | `uv run dbt test --project-dir dbt --profiles-dir dbt` (or `make dbt-test`) |
| Run a single dbt model | `uv run dbt run --select stg_carbon_intensity__national --project-dir dbt --profiles-dir dbt` |
| Install dbt packages | `uv run dbt deps --project-dir dbt --profiles-dir dbt` (or `make dbt-deps`) |
| Serve dbt docs on :8080 | `make dbt-docs` |
| Launch Streamlit dashboard | `make dashboard` |
| Lint / format (ruff) | `make lint` / `make format` |
| Run Python tests | `uv run pytest -q` |
| Run a single pytest | `uv run pytest tests/test_carbon_intensity_asset.py::test_raw_carbon_intensity__national_returns_dataframe` |
| Skip live-API smoke tests | `uv run pytest -m "not integration"` |
| Wipe local state | `make clean` (removes dbt `target/`, `dbt_packages/`, dagster logs) |

## Architecture

The repo is a three-stage pipeline: **Dagster ingests** raw API data into Snowflake (`UK_GRID.RAW.*`) → **dbt transforms** staging → intermediate → marts → **Streamlit** reads the marts. Each stage has conventions worth knowing before editing:

### Naming convention

Every asset, table, and dbt model follows `<stage>_<source>__<desc>` (single underscore between stage and source, **double underscore** before the description):

| Segment | Values | Example |
|---|---|---|
| `<stage>` | `raw`, `stg`, `int`, `fact`, `dim` | `raw` |
| `<source>` | logical source system — matches the dbt source `name:` and Dagster `group_name` | `carbon_intensity` |
| `__<desc>` | snake_case description of grain/content | `__national` |

Full examples: `raw_carbon_intensity__national`, `stg_neso__dno_polygons`, `dim_neso__dno_region`.

Mart models (`fact_*`, `dim_*`) that join across sources omit the source segment when the content is truly cross-source (e.g. `fact_carbon_intensity_hourly` rolls up one source so keeps it; a future `fact_grid_state` joining three sources would have no source segment).

The Dagster asset function name **is** the Snowflake table name (via the IO manager). The `name:` field in `dbt/models/sources.yml` must match exactly.

### Ingestion (`src/uk_grid/`)
- `src/uk_grid/definitions.py` is the Dagster entrypoint, registered via `[tool.dagster] module_name = "uk_grid.definitions"` in `pyproject.toml`. It loads every asset under `src/uk_grid/assets/` automatically (`dg.load_assets_from_modules`), so new assets only need to be added to a module in that package — no manual registration.
- One module per source domain under `src/uk_grid/assets/` (`carbon_intensity.py`, `grid_eso.py`, `met_office.py`, `neso_geo.py`). Only `raw_carbon_intensity__national` is fully implemented; the others are stubs that return empty DataFrames and are meant to be filled in by copying the carbon-intensity pattern (httpx + `tenacity` retry + Dagster output metadata for row counts and time ranges).
- Raw assets land in Snowflake via `SnowflakePandasIOManager`, configured in `src/uk_grid/resources.py`. All assets land in a single `RAW` schema (`UK_GRID.RAW.*`), controlled by `SNOWFLAKE_SCHEMA` in the environment (default `RAW`). Source identity is encoded in the table name (e.g. `raw_carbon_intensity__national`, `raw_neso__dno_polygons`). Do not override the schema per asset — the flat-schema convention is intentional.
- Settings are loaded from `.env` via `pydantic-settings` (`Settings` class in `resources.py`). The Carbon Intensity API needs no auth; only Met Office requires `MET_OFFICE_API_KEY`.

### Transformation (`dbt/`)
- Layered convention enforced via `dbt/dbt_project.yml`: `staging/` → views in schema `ANALYTICS_STAGING`, `intermediate/` → ephemeral (inlined into downstream SQL), `marts/` → tables in schema `ANALYTICS_MARTS`. The profile base schema is controlled by `SNOWFLAKE_DBT_SCHEMA` (default `ANALYTICS`). Don't change a model's layer without thinking about whether the materialisation default is still right.
- Staging models are 1:1 with sources — cleaning and type casts only, no joins or business logic. Joins/derivations belong in `intermediate/`; the queryable end product lives in `marts/`.
- Source freshness thresholds are set globally in `dbt/dbt_project.yml` (warn at 2h, error at 12h) and re-asserted per-table in `dbt/models/sources.yml`. Editing source schemas means editing both the Dagster asset's DataFrame columns and the matching table block in `sources.yml`.
- dbt packages (`dbt_utils`, `dbt_expectations`) are declared in `dbt/packages.yml`; run `make dbt-deps` after pulling changes.
- All dbt commands must include `--project-dir dbt --profiles-dir dbt`.

### Serving
- `src/uk_grid/dashboard/app.py` is a Streamlit app that reads from the `ANALYTICS_MARTS` schema in Snowflake.
- dbt docs are auto-published to GitHub Pages on every merge to `main` (see `.github/workflows/ci.yml`).

### CI
Every PR runs: ruff lint → pytest → `dbt parse` (validates SQL refs and Jinja without a warehouse connection). A separate `nightly-build.yml` workflow (to be added) will run the full `dbt build` + asset materialisation with Snowflake secrets. The CI workflow copies `dbt/profiles.yml.example` to `~/.dbt/profiles.yml` and passes `--project-dir dbt --profiles-dir dbt` consistently.

## Constraints to keep in mind

- **No incremental ingestion yet.** `raw_carbon_intensity__national` pulls the trailing 24h on every run; there is no partition definition or incremental dbt materialisation in place. If you add backfill support, you'll likely want Dagster `DailyPartitionsDefinition` + `materialized='incremental'` with `unique_key='interval_start_utc'` and a `merge` strategy — the README's "Engineering decisions" section commits to this pattern.
- **Tests marked `@pytest.mark.integration` hit live APIs.** The carbon-intensity smoke test will fail without network. Use `-m "not integration"` in offline contexts.
- **Snowflake credentials required for materialisation.** `uv run dagster dev` and `make dbt-build` both need a populated `.env`. The `dbt parse` step in CI is credential-free.

## Known-gotcha list (debugged the hard way — don't re-debug)

- **Don't use `from __future__ import annotations` in Dagster asset modules.** Dagster's `_validate_context_type_hint` (op_definition.py) inspects `params[0].annotation` directly without `get_type_hints()`, so PEP 563 string annotations never match the expected class objects and `@asset` registration fails with a confusingly self-referential error. Python 3.13 supports modern type hints natively without the future import.
- **Don't use `dagster-snowflake-pandas`'s built-in `SnowflakePandasIOManager` constructed via direct kwargs from a Settings singleton.** Dagster's `ConfigurableIOManager` config-resolution layer re-instantiates the IO manager via Pydantic `model_validate` at materialise time, discarding the in-memory config. The Snowflake driver then receives empty credentials and surfaces it as a misleading `250001 Incorrect username or password` error even though the credentials are correct. The fix is in `src/uk_grid/resources.py`: a custom `UKGridSnowflakeIOManager(dg.IOManager)` subclass that holds a `Settings` reference directly and bypasses the config layer entirely. If you need to write a new IO manager, follow that pattern.
- **`snowflake-connector-python` 4.x has a packaging bug** where some wheels ship without `externals_utils/externals_setup.py`, breaking even `import snowflake.connector`. Pinned to `>=3.14,<4.0` in `pyproject.toml`. Do not unpin without testing.
- **Hatchling editable install + src/ layout requires explicit `[tool.hatch.build.targets.wheel.sources]` mapping** (`"src/uk_grid" = "uk_grid"`) — without it, the editable install puts the project root on sys.path but not `src/`, so `import uk_grid` fails. The mapping is in `pyproject.toml`.
- **After changing `pyproject.toml`'s build config or `packages` field**, run `uv sync --reinstall-package uk-grid-carbon-pipeline` (or nuke `.venv` + `uv.lock` and re-sync) — `uv sync` alone won't regenerate the editable install path hook.
- **`.env` values with `$`, `#`, `"`, `'`, or `\` should be single-quoted** (e.g. `SNOWFLAKE_PASSWORD='your$pass'`). Dotenv treats unquoted `#` as a comment delimiter and `$` as variable interpolation.
- **Makefile dbt targets must source `.env` before invoking dbt** (`set -a && . ./.env && set +a && uv run dbt ...`). Dagster gets env vars via Python's `load_dotenv()` in `resources.py`, but dbt is a subprocess that doesn't read `.env` on its own.
- **macOS `Finder` duplicates** (`_staging__models 2.yml`, etc.) inside `dbt/` will fail `dbt parse`/`build` with a "two schema.yml entries for the same resource" error. Periodically clean them: `find dbt -name '* 2.*' -delete`.

## Specialist agent for this layer

There's a `.claude/agents/dagster-snowflake-engineer.md` agent purpose-built for debugging the Dagster + Snowflake integration. Invoke it via `Agent` tool with `subagent_type="dagster-snowflake-engineer"` for any future auth, IO manager, or RBAC issues. The agent's system prompt contains the institutional knowledge for the gotchas above.

## Source of truth for design decisions

`docs/architecture.md` is the canonical written rationale for Dagster-over-Airflow, dbt-core-over-Cloud, Snowflake-over-DuckDB, and uv-over-poetry. If a change touches those choices, update that document.
