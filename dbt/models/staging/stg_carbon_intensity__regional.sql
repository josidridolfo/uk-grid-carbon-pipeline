{{ config(materialized='view') }}

-- One-to-one with raw_carbon_intensity__regional: cleaning, type casting,
-- renaming. No business logic — that lives in intermediate/marts.
--
-- Type-coercion policy (matches stg_carbon_intensity__national):
-- intensity columns cast as numeric(6,1) (NOT integer) to preserve the
-- decimal precision the Carbon Intensity API occasionally returns.

with source as (
    select * from {{ source('raw_carbon_intensity', 'raw_carbon_intensity__regional') }}
),

renamed as (
    select
        cast(interval_start_utc as timestamp) as interval_start_utc,
        cast(interval_end_utc as timestamp) as interval_end_utc,
        cast(region_id as integer) as region_id,
        region_shortname,
        region_dnoregion,
        cast(intensity_forecast_gco2_per_kwh as numeric(6,1)) as intensity_forecast_gco2_per_kwh,
        cast(intensity_actual_gco2_per_kwh as numeric(6,1)) as intensity_actual_gco2_per_kwh,
        index_band,
        cast(_fetched_at_utc as timestamp) as fetched_at_utc
    from source
)

select * from renamed
