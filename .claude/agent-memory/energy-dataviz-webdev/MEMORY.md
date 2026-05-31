# Energy Dataviz Webdev — Memory Index

- [Dashboard tech stack decision](project_dashboard_stack.md) — Django + htmx + Tailwind + Alpine.js; Streamlit superseded; multi-page site at energy-project.ridol.fo
- [Choropleth library decision](project_choropleth_library.md) — MapLibre GL JS for choropleth (GeoJSON endpoint); Plotly kept for time-series sparklines only
- [Snowflake data access pattern](project_data_access_pattern.md) — Direct connector + Django cache (Redis, TTL 1800s); connection pool via AppConfig.ready()
- [Hosting decision](project_hosting_decision.md) — Hetzner CX22 + Caddy + Docker Compose; ~$5/mo; no cold starts; CNAME to ridol.fo
- [Dashboard test architecture](project_dashboard_tests.md) — Four-layer pytest-django strategy: PR CI (mocked), nightly Snowflake, weekly Playwright e2e
- [Streamlit Cloud gotchas](project_streamlit_cloud_gotchas.md) — SUPERSEDED; retained as historical record only
- [User profile](user_profile.md) — Portfolio-driven project, UK Skilled Worker Visa target, mid-July 2026 ship date
