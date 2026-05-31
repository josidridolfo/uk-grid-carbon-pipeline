---
name: choropleth-library
description: MapLibre GL JS (via /api/dno-regions.geojson Django endpoint) for choropleth; Plotly kept for time-series sparklines only
metadata:
  type: project
---

MapLibre GL JS is the chosen library for the UK DNO-region choropleth in the Django app. Plotly is kept for time-series sparklines only (24h carbon intensity line chart embedded via Django template + plotly.js).

**Why:** The `GEOGRAPHY` polygon column is native GeoJSON on the wire — Django view returns `JsonResponse(geojson_dict)` with no figure serialisation overhead. MapLibre renders at 60fps on mobile. Screenshot quality is superior to Plotly's canvas rasterisation. The htmx pattern works cleanly: map initialises once in client JS; htmx partial swaps update the stats panel beside the map without re-rendering the map itself. At 14 polygons Plotly choropleth would have worked too, but MapLibre is more legible as a portfolio skill for hiring managers in the energy sector.

**How to apply:** GeoJSON endpoint is `GET /api/dno-regions.geojson` — returns FeatureCollection with `dno_name`, `avg_carbon_intensity_gco2_kwh`, and `period_date` properties. Tooltip should read "DNO: {region} / {value} gCO2/kWh". Cache the GeoJSON view response with Django cache framework (TTL 1800s). Use Plotly JS (not MapLibre) for all time-series charts.

Related: [[dashboard-stack]], [[data-access-pattern]]
