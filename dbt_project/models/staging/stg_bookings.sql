with source as (
    select * from raw_bookings
)
select
    booking_id,
    try_cast(booking_date as date) as booking_date,
    customer_id,
    flight_id,
    booking_channel,
    fare_class,
    fare_family,
    cast(ticket_price_usd        as double) as ticket_price_usd,
    cast(ancillary_revenue_usd   as double) as ancillary_revenue_usd,
    cast(ticket_price_usd as double) + cast(ancillary_revenue_usd as double) as total_revenue_usd,
    cast(bags_count              as integer) as bags_count,
    cast(seat_selection_flag     as integer) as seat_selection_flag,
    booking_status,
    case
        when fare_class in ('Business', 'First') then 'Premium'
        when fare_family = 'Flex'                then 'Flexible Economy'
        else 'Standard Economy'
    end as revenue_category,
    case when cast(ancillary_revenue_usd as double) > 0 then 1 else 0 end as has_ancillary,
    case when cast(seat_selection_flag as integer) = 1 then 1 else 0 end as has_seat_selection
from source
where booking_status != 'Cancelled'
