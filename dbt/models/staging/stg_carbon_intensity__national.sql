{{ config(materialized='view') }}

-- One-to-one with the raw source: cleaning, type casting, renaming.
-- No business logic here — that lives in intermediate/marts.
--
-- Intensity columns cast to numeric(6,1) (was integer). The Carbon Intensity API
-- returns decimal values for some intervals (~145.7 gCO2/kWh); the previous
-- integer cast silently truncated these. numeric(6,1) preserves one decimal
-- place — enough precision for the analytical use cases without bloating
-- storage. The pure-function parser preserves the raw API values; this
-- staging model is the only place a precision policy is applied.

with source as (
    select * from {{ source('raw_carbon_intensity', 'raw_carbon_intensity__national') }}
),

renamed as (
    select
        cast(interval_start_utc as timestamp) as interval_start_utc,
        cast(interval_end_utc as timestamp) as interval_end_utc,
        cast(intensity_forecast_gco2_per_kwh as numeric(6,1)) as intensity_forecast_gco2_per_kwh,
        cast(intensity_actual_gco2_per_kwh as numeric(6,1)) as intensity_actual_gco2_per_kwh,
        index_band,
        cast(_fetched_at_utc as timestamp) as fetched_at_utc
    from source
)

select * from renamed
