# energy-project web

Django frontend for [energy-project.ridol.fo](https://energy-project.ridol.fo).
Sibling to `src/uk_grid/` (Dagster + dbt pipeline).

**Local dev:**
```bash
cp .env.example .env
# generate a secret key: python -c "import secrets; print(secrets.token_urlsafe(50))"
# edit .env — set DJANGO_SECRET_KEY and optionally SNOWFLAKE_* vars
docker compose up --build
# visit http://localhost:8000/
```

**Deploy:** see top-level `README.md` + `infra/` for Hetzner + Caddy setup (Phase 1a/1b).

Stack: Django 5 + htmx 2 + Tailwind CSS 3 + Postgres 16 + Gunicorn.
