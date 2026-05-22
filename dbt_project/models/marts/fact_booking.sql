with bookings as (
    select * from {{ ref('stg_bookings') }}
),
flights as (
    select
        flight_id,
        route_id,
        flight_date,
        flight_year,
        flight_month,
        flight_quarter,
        flight_status,
        delay_min,
        delay_category,
        seat_capacity
    from {{ ref('stg_flights') }}
),
customers as (
    select
        customer_id,
        customer_segment,
        loyalty_tier,
        loyalty_tier_rank,
        country,
        age_years
    from {{ ref('stg_customers') }}
)
select
    b.booking_id,
    b.booking_date,
    b.customer_id,
    b.flight_id,
    f.route_id,
    f.flight_date,
    f.flight_year,
    f.flight_month,
    f.flight_quarter,
    b.booking_channel,
    b.fare_class,
    b.fare_family,
    b.revenue_category,
    b.ticket_price_usd,
    b.ancillary_revenue_usd,
    b.total_revenue_usd,
    b.bags_count,
    b.has_ancillary,
    b.has_seat_selection,
    b.booking_status,
    c.customer_segment,
    c.loyalty_tier,
    c.loyalty_tier_rank,
    c.country          as customer_country,
    c.age_years        as customer_age,
    f.flight_status,
    f.delay_min,
    f.delay_category,
    -- Revenue per pax metrics
    b.ticket_price_usd + b.ancillary_revenue_usd as revenue_per_pax_usd
from bookings b
left join flights   f on b.flight_id   = f.flight_id
left join customers c on b.customer_id = c.customer_id
