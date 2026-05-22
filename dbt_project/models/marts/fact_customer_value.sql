{#-
    Customer-level aggregate: CLV, ancillary attach, premium conversion,
    booking recency, and a churn-risk label.

    Recency uses date '{{ var("reference_date") }}' as the anchor so the
    field stays meaningful as calendar time moves on. With CURRENT_DATE,
    every customer would drift into "High Risk" once the data ages past
    180 days, masking the real signal.
-#}
with bookings as (
    select * from {{ ref('fact_booking') }}
),
booking_summary as (
    select
        customer_id,
        count(distinct flight_id)                                                              as total_flights,
        count(booking_id)                                                                      as total_bookings,
        sum(total_revenue_usd)                                                                 as total_revenue_usd,
        avg(total_revenue_usd)                                                                 as avg_revenue_per_booking,
        sum(ancillary_revenue_usd)                                                             as total_ancillary_usd,
        sum(has_ancillary)                                                                     as bookings_with_ancillary,
        max(booking_date)                                                                      as last_booking_date,
        min(booking_date)                                                                      as first_booking_date,
        date_diff('day', max(booking_date)::date, date '{{ var("reference_date") }}')          as days_since_last_booking,
        count(distinct route_id)                                                               as distinct_routes_flown,
        sum(case when fare_class in ('Business', 'First') then 1 else 0 end)                  as premium_bookings,
        sum(case when flight_quarter = 1 then 1 else 0 end)                                   as q1_bookings,
        sum(case when flight_quarter = 2 then 1 else 0 end)                                   as q2_bookings,
        sum(case when flight_quarter = 3 then 1 else 0 end)                                   as q3_bookings,
        sum(case when flight_quarter = 4 then 1 else 0 end)                                   as q4_bookings
    from bookings
    group by customer_id
),
customers as (
    select * from {{ ref('dim_customer') }}
)
select
    c.customer_id,
    c.full_name,
    c.customer_segment,
    c.loyalty_tier,
    c.loyalty_tier_rank,
    c.tenure_months,
    c.total_points_earned,
    c.max_points_balance,
    c.total_support_tickets,
    c.avg_csat_score,
    coalesce(b.total_flights, 0)             as total_flights,
    coalesce(b.total_bookings, 0)            as total_bookings,
    coalesce(b.total_revenue_usd, 0)         as total_revenue_usd,
    b.avg_revenue_per_booking,
    coalesce(b.total_ancillary_usd, 0)       as total_ancillary_usd,
    coalesce(b.bookings_with_ancillary, 0)   as bookings_with_ancillary,
    b.last_booking_date,
    b.first_booking_date,
    coalesce(b.days_since_last_booking, 9999) as days_since_last_booking,
    coalesce(b.distinct_routes_flown, 0)     as distinct_routes_flown,
    coalesce(b.premium_bookings, 0)          as premium_bookings,
    case
        when coalesce(c.tenure_months, 0) > 0
        then round(coalesce(b.total_revenue_usd, 0) / c.tenure_months * 12, 2)
        else 0
    end as annualized_revenue_usd,
    round(
        coalesce(b.bookings_with_ancillary, 0)::double / nullif(b.total_bookings, 0) * 100,
    1) as ancillary_attach_rate_pct,
    round(
        coalesce(b.premium_bookings, 0)::double / nullif(b.total_bookings, 0) * 100,
    1) as premium_conversion_rate_pct,
    round(
        coalesce(b.total_bookings, 0)::double / nullif(c.tenure_months, 0),
    2) as booking_frequency_per_month,
    {#- Recency-based churn risk anchored to reference date. -#}
    case
        when coalesce(b.days_since_last_booking, 9999) > 180
            and coalesce(b.total_flights, 0) >= 3
        then 'High Risk'
        when coalesce(b.days_since_last_booking, 9999) > 90
        then 'Medium Risk'
        else 'Low Risk'
    end as churn_risk_label
from customers c
left join booking_summary b on c.customer_id = b.customer_id
