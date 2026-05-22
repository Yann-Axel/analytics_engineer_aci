with routes as (
    select * from {{ ref('stg_routes') }}
),
airports as (
    select * from {{ ref('stg_airports') }}
),
fare as (
    select * from synth_fare_details
)
select
    r.route_id,
    r.route_label,
    r.route_type,
    r.haul_category,
    r.distance_km,
    r.block_time_min,
    r.block_time_h,
    r.origin_airport_code,
    o.airport_name   as origin_airport_name,
    o.city           as origin_city,
    o.country        as origin_country,
    r.destination_airport_code,
    d.airport_name   as destination_airport_name,
    d.city           as destination_city,
    d.country        as destination_country,
    f.aircraft_type_assigned,
    f.seat_capacity,
    f.fuel_cost_usd,
    f.crew_cost_usd,
    f.airport_fees_usd,
    f.total_operating_cost_usd,
    f.breakeven_load_factor_pct,
    f.avg_competitor_price_usd
from routes r
left join airports o on r.origin_airport_code      = o.airport_code
left join airports d on r.destination_airport_code = d.airport_code
left join fare     f on r.route_id                 = f.route_id
