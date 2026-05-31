---
name: geo-layer
description: DNO polygon geo layer: raw_neso__dno_polygons asset reprojects EPSG:27700→4326, stg_neso__dno_polygons casts to GEOGRAPHY, dim_neso__dno_region joins to reconciliation seed
metadata:
  type: project
---

The geo layer is a foundation for spatial joins (regional carbon intensity, weather stations → region).

**Source:** `data/reference/gb_dno_licence_areas_20240503.geojson` — NESO Open Data, EPSG:27700, 14 features. Properties: `ID` (10-23), `Name`, `DNO`, `Area`, `DNO_Full`.

**Asset:** `raw_neso__dno_polygons` in `uk_grid/assets/neso_geo.py`
- Reprojects EPSG:27700 → EPSG:4326 using `pyproj.Transformer(always_xy=True)` + `shapely.ops.transform`.
- Returns flat DataFrame: `geojson_id`, `area_name`, `dno_code`, `dno_full`, `geometry_wkt` (WKT string).
- Lands in schema `RAW_NESO` via `metadata={"schema": "RAW_NESO"}`.
- No auto-materialise policy — static reference data, materialise manually.

**Reconciliation seed:** `seeds/dno_region_mapping.csv` — bridges Carbon Intensity API `regionid` (1-14) to GeoJSON `ID` (10-23). Three region names differ between the two sources. This seed is the single source of truth for the cross-walk.

**dbt models (all implemented as of 2026-05-31):**
- `stg_neso__dno_polygons` — view; casts `geometry_wkt` to `GEOGRAPHY` via `TO_GEOGRAPHY()`. Tests: `geojson_id` unique+not_null, `dno_code` accepted_values, `polygon` not_null.
- `dim_dno_region` — table; joins staging to seed on `geojson_id`; PK is `api_regionid` (surrogate for Carbon Intensity joins); also exposes `geojson_id` (unique), `polygon` (GEOGRAPHY), `polygon_centroid` (ST_CENTROID). Model-level test: `dbt_expectations.expect_table_row_count_to_equal: 14`. Note: marts model is named `dim_dno_region`, not `dim_neso__dno_region` (no source prefix in marts layer).

**dno_code accepted values:** UKPN, NGED, NPG, SPEN, SSEN, ENWL (6 values, 14 rows because some DNOs cover multiple regions).

**Why reprojection lives in the Dagster asset (not preprocessing the file):** keeps lineage explicit in the Dagster asset graph; the raw GeoJSON stays unmodified as the source of record.

**How to apply:** Future spatial assets (weather stations → region, charge points → region) join to `dim_dno_region.polygon` via `ST_CONTAINS`/`ST_WITHIN` using `api_regionid` as the foreign key to Carbon Intensity data.
