with source as (
    select * from raw_flights
)
select
    flight_id,
    flight_number,
    route_id,
    try_cast(flight_date as date) as flight_date,
    date_part('year',  try_cast(flight_date as date)) as flight_year,
    date_part('month', try_cast(flight_date as date)) as flight_month,
    date_part('quarter', try_cast(flight_date as date)) as flight_quarter,
    try_cast(scheduled_departure as timestamp) as scheduled_departure,
    try_cast(actual_departure    as timestamp) as actual_departure,
    try_cast(scheduled_arrival   as timestamp) as scheduled_arrival,
    try_cast(actual_arrival      as timestamp) as actual_arrival,
    aircraft_type,
    cast(seat_capacity as integer) as seat_capacity,
    flight_status,
    coalesce(try_cast(delay_min as integer), 0) as delay_min,
    case
        when flight_status = 'Cancelled'          then 'Cancelled'
        when coalesce(try_cast(delay_min as integer), 0) = 0   then 'On-Time'
        when coalesce(try_cast(delay_min as integer), 0) <= 15  then 'Minor Delay'
        when coalesce(try_cast(delay_min as integer), 0) <= 60  then 'Moderate Delay'
        else 'Major Delay'
    end as delay_category
from source
