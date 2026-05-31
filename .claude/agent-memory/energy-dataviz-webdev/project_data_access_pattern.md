---
name: data-access-pattern
description: snowflake-connector-python direct from Django views + Redis cache TTL 1800s; connection pool via AppConfig.ready()
metadata:
  type: project
---

Data access pattern: `snowflake-connector-python` called directly from Django views. Connection pool initialised once in `AppConfig.ready()` and stored on the app config object. Redis cache backend, TTL 1800s, via Django's `cache.get/set`.

Aggregation is pushed to Snowflake SQL — Django views receive small result sets (e.g., 14 rows for the regional choropleth). Never pull raw half-hourly rows into Python.

Authentication: RSA key-pair (not password). Private key path injected as env var, mounted as read-only bind mount in Docker Compose. Snowflake REPORTER role (read-only on ANALYTICS_MARTS).

**Why:** No Parquet-to-disk (fragile sync, stale data risk). No FastAPI layer (unnecessary hop, doubles infra). Direct connector with Django cache is the simplest path that handles the data volumes in this project. Regional mart is ~672 rows/day (14 regions × 48 half-hours) — no streaming or pagination needed.

**How to apply:** All Snowflake calls in `carbon/` app. Use `@django.core.cache.cache` decorators or explicit `cache.get/set` with a computed cache key that includes the query date. Never interpolate user input into SQL. Mark Snowflake integration tests with `pytest.mark.snowflake` and gate them to nightly CI.

Related: [[dashboard-stack]], [[hosting-decision]]
