---
name: dashboard-tests
description: Four-layer Django test strategy: pytest-django view/URL tests, htmx fragment tests, Plotly unit tests, Snowflake nightly, Playwright weekly
metadata:
  type: project
---

Test architecture for the Django data product site. All layers use pytest-django (not Django's built-in TestCase).

**PR CI (every push — no Snowflake secrets needed):**
- Django view/URL tests: mock Snowflake connector, assert HTTP 200, assert key context variables present
- htmx fragment endpoint tests: assert 200, assert specific HTML fragments (e.g., `gCO2/kWh` unit present in response body)
- GeoJSON endpoint schema tests: assert FeatureCollection structure, assert required properties on each feature
- Plotly figure-builder unit tests: assert correct trace types, correct axis labels and units, no empty data

**Nightly CI (Snowflake secrets available, gated with `pytest.mark.snowflake`):**
- Data contract tests: row count > 0, no nulls in key columns, value ranges sane (0–600 gCO2/kWh), schema matches expected columns

**Post-deploy / weekly:**
- Playwright e2e against live `energy-project.ridol.fo`: map renders, region tooltip shows gCO2/kWh, time-series chart loads within 10 seconds

Visual regression snapshots rejected — Plotly version bumps generate false positive diffs.

**How to apply:** All tests in `web/tests/`. Use `@pytest.mark.snowflake` to gate nightly tests. Mock Snowflake with `unittest.mock.patch` in PR CI.

Related: [[dashboard-stack]], [[choropleth-library]]
