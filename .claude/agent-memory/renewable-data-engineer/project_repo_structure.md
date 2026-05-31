---
name: repo-structure
description: Post-refactor layout: src/uk_grid/ for Python, dbt/ for all dbt artefacts, tests/ for pytest only.
metadata:
  type: project
---

Repo was refactored to standard `src` layout and consolidated dbt directory.

**Why:** Clean separation between Python package and dbt project; all dbt commands share a single `--project-dir dbt --profiles-dir dbt` flag; `src/` layout avoids import-shadowing issues.

**Key layout facts:**
- Python package: `src/uk_grid/` (assets, dashboard, resources, definitions)
- Dashboard moved from root `dashboard/` to `src/uk_grid/dashboard/app.py`
- dbt artefacts: `dbt/` (dbt_project.yml, packages.yml, profiles.yml.example, models/, seeds/, macros/, tests/)
- Python tests: `tests/` (pytest only; no dbt tests here)
- `pyproject.toml`: `packages = ["src/uk_grid"]` for hatchling; `module_name = "uk_grid.definitions"` for Dagster (unchanged — importable name is unaffected by src layout)
- `neso_geo.py` path computation: `Path(__file__).parent.parent.parent.parent / "data" / "reference" / ...` (4 parents: assets/ → uk_grid/ → src/ → repo root)

**How to apply:** Always reference `src/uk_grid/` for Python asset paths. Always pass `--project-dir dbt --profiles-dir dbt` (or `make dbt-*`). The Dagster module name `uk_grid.definitions` is unchanged — do not add `src.` prefix.
