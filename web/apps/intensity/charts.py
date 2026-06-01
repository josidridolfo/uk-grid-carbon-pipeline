"""
Pure chart-building helpers for apps.intensity.

These functions take pre-fetched data (list[dict]) and return a Plotly figure
as a plain dict (not a plotly.graph_objects.Figure). Plain dicts are:
  - easier to unit-test (no Plotly import required in tests)
  - safe to pass to json.dumps() directly
  - serialisable by Django's template engine without a custom encoder

Color scheme: CSS variables var(--color-accent) and var(--color-muted) are
passed directly as line.color values. Plotly supports any valid CSS color
string, so the chart automatically inherits the active theme when the browser
resolves the variable at paint time.

NOTE: CSS variable strings are passed as-is; they resolve in the browser via
Plotly's inline-style path. Plotly.js >= 2.x supports CSS custom properties
in color fields when the underlying renderer evaluates them against the DOM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


# Intensity band thresholds (gCO2/kWh) — Carbon Intensity API definitions.
BAND_THRESHOLDS = [
    (0, 50, "very-low", "Very Low"),
    (50, 100, "low", "Low"),
    (100, 200, "moderate", "Moderate"),
    (200, 300, "high", "High"),
    (300, float("inf"), "very-high", "Very High"),
]


def intensity_band(value: float | None) -> tuple[str, str]:
    """
    Return (variant, label) for a gCO2/kWh value.

    variant matches the badge.html component variants: very-low, low,
    moderate, high, very-high.  Returns ("default", "Unknown") for None.
    """
    if value is None:
        return ("default", "Unknown")
    for lo, hi, variant, label in BAND_THRESHOLDS:
        if lo <= value < hi:
            return (variant, label)
    return ("very-high", "Very High")


def _iso_or_str(dt: Any) -> str:
    """Convert a datetime (tz-aware or naive) or any value to an ISO-8601 string."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def build_national_intensity_figure(rows: list[dict]) -> dict:
    """
    Build a Plotly time-series figure dict from FACT_CARBON_INTENSITY_HOURLY rows.

    Parameters
    ----------
    rows : list[dict]
        Each dict must have keys:
          - hour_start_utc                      (datetime or str)
          - mean_intensity_actual_gco2_per_kwh  (float | None)
          - mean_intensity_forecast_gco2_per_kwh (float | None)

        An empty list is valid — two empty traces are returned.

    Returns
    -------
    dict
        A Plotly figure dict with "data" (list of 2 trace dicts) and "layout".
        Safe to pass to json.dumps() and to Plotly.newPlot() in the browser.
    """
    x_vals = [_iso_or_str(r["hour_start_utc"]) for r in rows]
    y_actual = [r.get("mean_intensity_actual_gco2_per_kwh") for r in rows]
    y_forecast = [r.get("mean_intensity_forecast_gco2_per_kwh") for r in rows]

    actual_trace: dict = {
        "type": "scatter",
        "mode": "lines",
        "name": "Actual",
        "x": x_vals,
        "y": y_actual,
        "line": {
            "color": "var(--color-accent)",
            "width": 2,
            "dash": "solid",
        },
        "hovertemplate": "%{x|%H:%M UTC}<br>Actual: %{y:.0f} gCO₂/kWh<extra></extra>",
    }

    forecast_trace: dict = {
        "type": "scatter",
        "mode": "lines",
        "name": "Forecast",
        "x": x_vals,
        "y": y_forecast,
        "line": {
            "color": "var(--color-muted)",
            "width": 1.5,
            "dash": "dash",
        },
        "hovertemplate": "%{x|%H:%M UTC}<br>Forecast: %{y:.0f} gCO₂/kWh<extra></extra>",
    }

    layout: dict = {
        "title": {
            "text": "Carbon Intensity — Past 24 Hours",
            "font": {"size": 16},
        },
        "xaxis": {
            "title": {"text": "Time (UTC)"},
            "type": "date",
            "tickformat": "%H:%M",
            "showgrid": True,
            "gridcolor": "rgba(100,116,139,0.15)",
        },
        "yaxis": {
            "title": {"text": "Carbon Intensity (gCO₂/kWh)"},
            "rangemode": "tozero",
            "showgrid": True,
            "gridcolor": "rgba(100,116,139,0.15)",
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        "margin": {"l": 60, "r": 20, "t": 60, "b": 50},
        "hovermode": "x unified",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, system-ui, sans-serif", "size": 12},
        "annotations": [
            {
                "text": "Source: National Grid ESO Carbon Intensity API",
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": -0.12,
                "showarrow": False,
                "font": {"size": 10, "color": "rgba(100,116,139,0.8)"},
                "xanchor": "left",
            }
        ],
    }

    return {"data": [actual_trace, forecast_trace], "layout": layout}
