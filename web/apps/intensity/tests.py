"""
TDD tests for apps.intensity.

Run with: cd web && pytest apps/intensity/tests.py -v
Or full suite: cd web && pytest

Tests 1-4 run without Snowflake credentials.
Test 5 is marked @pytest.mark.integration and is skipped in CI.
"""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.template.loader import render_to_string


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_rows(n=24):
    """Return n hourly rows of fixture data as list[dict], newest-last."""
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = []
    for i in range(n):
        hour = now - timedelta(hours=(n - 1 - i))
        rows.append(
            {
                "hour_start_utc": hour,
                "mean_intensity_actual_gco2_per_kwh": 180.0 - i * 2.0,
                "mean_intensity_forecast_gco2_per_kwh": 182.0 - i * 2.0,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Test 1: pure function — valid figure dict
# ---------------------------------------------------------------------------


def test_build_national_intensity_figure_returns_valid_plotly_dict():
    """Pass 24 fixture rows; returned dict must have data (2 traces) and layout."""
    from apps.intensity.charts import build_national_intensity_figure

    rows = make_rows(24)
    fig = build_national_intensity_figure(rows)

    assert isinstance(fig, dict), "Must return a plain dict, not a Plotly Figure object"
    assert "data" in fig, "Must contain 'data' key"
    assert "layout" in fig, "Must contain 'layout' key"

    assert len(fig["data"]) == 2, "Must have exactly 2 traces (actual + forecast)"

    trace_names = {t.get("name", "").lower() for t in fig["data"]}
    assert any("actual" in n for n in trace_names), "One trace must be named 'actual'"
    assert any("forecast" in n for n in trace_names), "One trace must be named 'forecast'"

    layout = fig["layout"]
    assert "title" in layout, "layout must have 'title'"
    assert "xaxis" in layout, "layout must have 'xaxis'"
    assert "yaxis" in layout, "layout must have 'yaxis'"

    # y-axis label must include units
    yaxis_title = layout["yaxis"].get("title", "")
    assert "gCO2" in yaxis_title or "kWh" in yaxis_title, (
        f"y-axis title '{yaxis_title}' must include unit text (gCO2 or kWh)"
    )


# ---------------------------------------------------------------------------
# Test 2: empty data — graceful empty traces
# ---------------------------------------------------------------------------


def test_build_national_intensity_figure_handles_empty_rows():
    """Empty list in → figure dict with 2 traces each having x=[] and y=[]."""
    from apps.intensity.charts import build_national_intensity_figure

    fig = build_national_intensity_figure([])

    assert isinstance(fig, dict)
    assert len(fig["data"]) == 2, "Must still return 2 traces even when no data"

    for trace in fig["data"]:
        assert trace.get("x") == [] or trace.get("x") is None or list(trace.get("x", [])) == [], (
            f"Trace x values should be empty, got: {trace.get('x')}"
        )
        assert trace.get("y") == [] or trace.get("y") is None or list(trace.get("y", [])) == [], (
            f"Trace y values should be empty, got: {trace.get('y')}"
        )


# ---------------------------------------------------------------------------
# Test 3: view renders 200 with mock query
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_national_intensity_view_renders_with_mock_query(client):
    """View returns 200, uses correct template, injects expected context keys."""
    from django.core.cache import cache

    cache.clear()

    rows = make_rows(24)
    with patch("apps.intensity.views.fetch_national_intensity_rows", return_value=rows):
        response = client.get("/intensity/national/")

    assert response.status_code == 200

    template_names = [t.name for t in response.templates]
    assert "intensity/national.html" in template_names, (
        f"Expected 'intensity/national.html' in templates, got: {template_names}"
    )

    ctx = response.context
    assert "figure_json" in ctx, "Context must include 'figure_json'"
    assert "current_value" in ctx, "Context must include 'current_value'"
    assert "current_band" in ctx, "Context must include 'current_band'"
    assert "hero_subhead" in ctx, "Context must include 'hero_subhead'"

    # figure_json must be valid JSON
    fig = json.loads(ctx["figure_json"])
    assert "data" in fig
    assert "layout" in fig


# ---------------------------------------------------------------------------
# Test 4: cache hit skips Snowflake
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_national_intensity_view_cache_hit_skips_snowflake(client):
    """Second request within TTL must not call fetch_national_intensity_rows again."""
    from django.core.cache import cache

    cache.clear()

    rows = make_rows(24)
    with patch(
        "apps.intensity.views.fetch_national_intensity_rows", return_value=rows
    ) as mock_fetch:
        # First request — populates cache
        response1 = client.get("/intensity/national/")
        assert response1.status_code == 200

        # Second request — should hit cache
        response2 = client.get("/intensity/national/")
        assert response2.status_code == 200

    assert mock_fetch.call_count == 1, (
        f"fetch_national_intensity_rows should have been called exactly once, "
        f"but was called {mock_fetch.call_count} times"
    )


# ---------------------------------------------------------------------------
# Test 5: data-shape contract (integration — requires Snowflake creds)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skip(reason="Requires live Snowflake credentials — run locally with creds set")
def test_fetch_national_intensity_rows_returns_expected_columns():
    """
    Integration test: queries FACT_CARBON_INTENSITY_HOURLY and validates shape.

    Run locally with:
        SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=... \\
        pytest apps/intensity/tests.py::test_fetch_national_intensity_rows_returns_expected_columns \\
        -v -m integration
    """
    from apps.intensity.data import fetch_national_intensity_rows

    rows = fetch_national_intensity_rows()

    assert len(rows) > 0, "Expected at least one row from the last 24 hours"

    required_cols = {
        "hour_start_utc",
        "mean_intensity_actual_gco2_per_kwh",
        "mean_intensity_forecast_gco2_per_kwh",
    }
    assert required_cols.issubset(rows[0].keys()), (
        f"Missing columns. Expected {required_cols}, got {set(rows[0].keys())}"
    )

    # Non-null check on first row
    first = rows[0]
    assert first["hour_start_utc"] is not None
    assert first["mean_intensity_actual_gco2_per_kwh"] is not None


# ---------------------------------------------------------------------------
# Component composition tests for intensity/national.html
# ---------------------------------------------------------------------------


_TEMPLATE_CTX = {
    "figure_json": "{}",
    "current_value": 145,
    "current_band": "Moderate",
    "current_band_variant": "moderate",
    "hero_subhead": "145 gCO₂/kWh — Moderate",
}


def test_national_template_uses_hero_component():
    """intensity/national.html must include the hero component."""
    html = render_to_string("intensity/national.html", _TEMPLATE_CTX)
    assert 'data-testid="hero"' in html


def test_national_template_uses_metric_tile_component():
    """intensity/national.html must include the metric_tile component."""
    html = render_to_string("intensity/national.html", _TEMPLATE_CTX)
    assert 'data-testid="metric-tile"' in html


def test_national_template_uses_map_container_component():
    """intensity/national.html must include the map_container component."""
    html = render_to_string("intensity/national.html", _TEMPLATE_CTX)
    assert 'data-testid="map-container"' in html


def test_national_template_injects_figure_json():
    """intensity/national.html must output figure_json in the data script block."""
    ctx = dict(_TEMPLATE_CTX)
    ctx["figure_json"] = '{"data": [], "layout": {}}'
    html = render_to_string("intensity/national.html", ctx)
    assert ctx["figure_json"] in html
