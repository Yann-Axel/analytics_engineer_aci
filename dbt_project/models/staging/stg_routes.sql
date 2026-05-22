with source as (
    select * from raw_routes
),
enriched as (
    select
        route_id,
        origin_airport_code,
        destination_airport_code,
        route_id || ': ' || origin_airport_code || ' → ' || destination_airport_code as route_label,
        route_type,
        cast(distance_km     as integer) as distance_km,
        cast(block_time_min  as integer) as block_time_min,
        round(cast(block_time_min as double) / 60.0, 2) as block_time_h,
        case
            when route_type = 'Domestic'      then 'Domestic'
            when cast(distance_km as integer) > 5000 then 'Long-Haul'
            when cast(distance_km as integer) > 2000 then 'Medium-Haul'
            else 'Regional'
        end as haul_category
    from source
)
select * from enriched
