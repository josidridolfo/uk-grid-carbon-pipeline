{{ config(materialized='table') }}

-- Aggregate the half-hourly staging data to hourly grain for easier dashboard use.
-- This is the first end-to-end queryable mart: stg → fact, no joins yet.
-- Next: add dim_date and dim_region joins once those models are built.

with hourly as (
    select
        date_trunc('hour', interval_start_utc) as hour_start_utc,
        avg(intensity_forecast_gco2_per_kwh) as mean_intensity_forecast_gco2_per_kwh,
        avg(intensity_actual_gco2_per_kwh) as mean_intensity_actual_gco2_per_kwh,
        min(intensity_actual_gco2_per_kwh) as min_intensity_actual_gco2_per_kwh,
        max(intensity_actual_gco2_per_kwh) as max_intensity_actual_gco2_per_kwh,
        count(*) as half_hour_intervals_covered
    from {{ ref('stg_carbon_intensity__national') }}
    group by 1
)

select
    hour_start_utc,
    hour_start_utc + interval '1' hour as hour_end_utc,
    mean_intensity_forecast_gco2_per_kwh,
    mean_intensity_actual_gco2_per_kwh,
    min_intensity_actual_gco2_per_kwh,
    max_intensity_actual_gco2_per_kwh,
    half_hour_intervals_covered
from hourly
