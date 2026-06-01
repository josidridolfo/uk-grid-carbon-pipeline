{{ config(materialized='table') }}

-- Half-hourly carbon intensity for each of the 14 GB DNO licence areas,
-- joined to dim_dno_region so downstream consumers can render choropleths
-- and do spatial joins (point-in-polygon for weather stations, charge
-- points, postcode lookups, etc.).
--
-- INNER JOIN intentionally filters out the 4 aggregate regions
-- (regionid 15-17: England/Scotland/Wales rollups; regionid 18: GB total).
-- Those have no DNO polygon to render on a map and would only add NULL-
-- polygon rows to the choropleth source data. If you need them, materialise
-- a separate fact_regional_carbon_intensity__aggregates mart from the same
-- staging view — staging keeps all 18 region rows.
--
-- Schema:
--   - api_regionid: surrogate key, 1-14 (one of the seed's join keys)
--   - dno_code / dno_full_current / nation: from dim_dno_region; current
--     post-2021 DNO names
--   - polygon: GEOGRAPHY (EPSG:4326); ready for ST_CONTAINS / ST_WITHIN joins
--   - polygon_centroid: GEOGRAPHY POINT; useful for label placement and
--     "nearest DNO region" lookups
--
-- Phase 5's choropleth view materialises a recent-window slice of this mart
-- as figure JSON via Plotly.

with regional as (
    select * from {{ ref('stg_carbon_intensity__regional') }}
),

dim as (
    select * from {{ ref('dim_dno_region') }}
)

select
    regional.interval_start_utc,
    regional.interval_end_utc,
    dim.api_regionid,
    dim.api_shortname                                 as region_shortname,
    dim.dno_code,
    dim.dno_full_current,
    dim.nation,
    regional.intensity_forecast_gco2_per_kwh,
    regional.intensity_actual_gco2_per_kwh,           -- always NULL for regional; kept for schema parity
    regional.index_band,
    dim.polygon,
    dim.polygon_centroid,
    regional.fetched_at_utc
from regional
inner join dim on regional.region_id = dim.api_regionid
