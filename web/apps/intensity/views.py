"""
Views for apps.intensity.

NationalIntensityView
---------------------
  - Authenticates to Snowflake as REPORTER via get_snowflake_connection().
  - Caches query result for 1800 s (30 min) — acceptable staleness for this
    data cadence (Carbon Intensity API updates every 30 min).
  - Builds a Plotly figure dict via build_national_intensity_figure().
  - Serialises to JSON and passes to the template as figure_json.

Cache key: "national_intensity_24h"
Cache backend: LocMemCache (per-worker; acceptable at this traffic level).
"""

from __future__ import annotations

import json
import logging

from django.core.cache import cache
from django.views.generic import TemplateView

from apps.intensity.charts import build_national_intensity_figure, intensity_band
from apps.intensity.data import fetch_national_intensity_rows

logger = logging.getLogger(__name__)

_CACHE_KEY = "national_intensity_24h"
_CACHE_TTL = 1800  # 30 minutes


class NationalIntensityView(TemplateView):
    """
    /intensity/national/ — UK national carbon intensity, past 24 hours.
    """

    template_name = "intensity/national.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        rows = cache.get(_CACHE_KEY)
        if rows is None:
            try:
                rows = fetch_national_intensity_rows()
                cache.set(_CACHE_KEY, rows, _CACHE_TTL)
            except Exception:
                logger.exception("Failed to fetch national intensity rows from Snowflake")
                rows = []

        figure = build_national_intensity_figure(rows)
        # Serialise datetimes: default=str catches any non-serialisable objects
        # (e.g. tz-aware datetimes already converted to ISO strings in charts.py,
        # but this is a belt-and-braces guard).
        context["figure_json"] = json.dumps(figure, default=str)

        # Derive current reading from the most recent actual row
        current_value = None
        if rows:
            last_row = rows[-1]
            current_value = last_row.get("mean_intensity_actual_gco2_per_kwh")

        current_display = round(current_value) if current_value is not None else None
        context["current_value"] = current_display if current_display is not None else "—"

        band_variant, band_label = intensity_band(current_value)
        context["current_band"] = band_label
        context["current_band_variant"] = band_variant

        # Pre-built subhead string for the hero component
        if current_display is not None:
            context["hero_subhead"] = (
                f"{current_display} gCO₂/kWh — {band_label}"
            )
        else:
            context["hero_subhead"] = "No data available for the past 24 hours."

        return context
