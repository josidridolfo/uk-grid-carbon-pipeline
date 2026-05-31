{{ config(materialized='view') }}

-- One-to-one with raw_neso.raw_neso__dno_polygons: cast geometry_wkt to Snowflake GEOGRAPHY.
-- No business logic here — the join to the reconciliation seed lives in marts.

with source as (
    select * from {{ source('raw_neso', 'raw_neso__dno_polygons') }}
),

typed as (
    select
        cast(geojson_id as integer)          as geojson_id,
        cast(area_name as varchar)           as area_name,
        cast(dno_code as varchar)            as dno_code,
        cast(dno_full as varchar)            as dno_full,
        to_geography(geometry_wkt)           as polygon
    from source
)

select * from typed
