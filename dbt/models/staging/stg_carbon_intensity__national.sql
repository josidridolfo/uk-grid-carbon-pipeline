{{ config(materialized='view') }}

-- One-to-one with the raw source: cleaning, type casting, renaming.
-- No business logic here — that lives in intermediate/marts.

with source as (
    select * from {{ source('raw_carbon_intensity', 'raw_carbon_intensity__national') }}
),

renamed as (
    select
        cast(interval_start_utc as timestamp) as interval_start_utc,
        cast(interval_end_utc as timestamp) as interval_end_utc,
        cast(intensity_forecast_gco2_per_kwh as integer) as intensity_forecast_gco2_per_kwh,
        cast(intensity_actual_gco2_per_kwh as integer) as intensity_actual_gco2_per_kwh,
        index_band,
        cast(_fetched_at_utc as timestamp) as fetched_at_utc
    from source
)

select * from renamed
