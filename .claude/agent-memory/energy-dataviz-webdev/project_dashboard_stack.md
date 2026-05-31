---
name: dashboard-stack
description: Django + htmx + Tailwind + Alpine.js chosen; Streamlit superseded; multi-page data product at energy-project.ridol.fo
metadata:
  type: project
---

Django is the confirmed stack. Streamlit is superseded and its files (`src/uk_grid/dashboard/app.py`, `streamlit`/`altair` deps in `pyproject.toml`) should be deleted on Phase 1 day one.

Project structure: Django app lives at `web/` (sibling to `dbt/`, `src/`, `infra/`). Django apps on day one: `core` (site chrome, health check) and `carbon` (all carbon-intensity views, chart builders, GeoJSON endpoint). No blog app until after July ship.

Frontend: htmx + Tailwind CSS + Alpine.js for small client-side interactivity. No DRF, no Vue, no React. Plotly JS embedded via Django templates for time-series sparklines. MapLibre GL JS for the choropleth map, fed by a `/api/dno-regions.geojson` endpoint.

Deployment target: `energy-project.ridol.fo` (custom subdomain of `ridol.fo`). Hetzner CX22 + Caddy + Docker Compose.

**Why:** Owner wants room to iterate beyond a single page, has a custom domain, and needs hiring-manager-legible full-stack portfolio artefact. Django+htmx is squarely in the webdev agent's wheelhouse and reads as "knows the full stack" to energy sector hiring managers.

**How to apply:** Suggest Django views, htmx partials, and Tailwind templates for all new UI work. Do not suggest Streamlit for anything in this project.

Related: [[choropleth-library]], [[data-access-pattern]], [[hosting-decision]], [[dashboard-tests]]
