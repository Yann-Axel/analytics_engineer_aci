with flights as (
    select * from {{ ref('stg_flights') }}
),
bookings_agg as (
    select
        flight_id,
        count(*)                          as booked_seats,
        sum(ticket_price_usd)             as ticket_revenue_usd,
        sum(ancillary_revenue_usd)        as ancillary_revenue_usd,
        sum(total_revenue_usd)            as total_revenue_usd,
        avg(ticket_price_usd)             as avg_ticket_price_usd,
        sum(has_ancillary)                as pax_with_ancillary,
        sum(has_seat_selection)           as pax_with_seat_selection,
        count(case when fare_class in ('Business', 'First') then 1 end) as premium_pax
    from {{ ref('stg_bookings') }}
    group by flight_id
),
reviews_agg as (
    select
        flight_id,
        count(*)                    as review_count,
        avg(nps_score)              as avg_nps_score,
        sum(case when nps_category = 'Promoter'  then 1 else 0 end) as promoters,
        sum(case when nps_category = 'Detractor' then 1 else 0 end) as detractors
    from {{ ref('stg_reviews') }}
    group by flight_id
)
select
    f.flight_id,
    f.flight_number,
    f.route_id,
    f.flight_date,
    f.flight_year,
    f.flight_month,
    f.flight_quarter,
    f.aircraft_type,
    f.seat_capacity,
    f.flight_status,
    f.delay_min,
    f.delay_category,
    coalesce(b.booked_seats, 0)              as booked_seats,
    coalesce(b.ticket_revenue_usd, 0)        as ticket_revenue_usd,
    coalesce(b.ancillary_revenue_usd, 0)     as ancillary_revenue_usd,
    coalesce(b.total_revenue_usd, 0)         as total_revenue_usd,
    b.avg_ticket_price_usd,
    coalesce(b.pax_with_ancillary, 0)        as pax_with_ancillary,
    coalesce(b.pax_with_seat_selection, 0)   as pax_with_seat_selection,
    coalesce(b.premium_pax, 0)               as premium_pax,
    -- Load factor
    round(
        coalesce(b.booked_seats, 0)::double / nullif(f.seat_capacity, 0) * 100,
    1) as load_factor_pct,
    -- Yield (revenue per available seat km) — route distance joined via dim_route
    r.distance_km,
    r.total_operating_cost_usd,
    coalesce(b.total_revenue_usd, 0) - r.total_operating_cost_usd as estimated_margin_usd,
    -- Ancillary attach rate
    round(
        coalesce(b.pax_with_ancillary, 0)::double / nullif(b.booked_seats, 0) * 100,
    1) as ancillary_attach_rate_pct,
    -- NPS
    coalesce(r2.review_count, 0)  as review_count,
    r2.avg_nps_score,
    coalesce(r2.promoters, 0)     as promoter_count,
    coalesce(r2.detractors, 0)    as detractor_count,
    -- NPS = (promoters - detractors) / total * 100
    case
        when coalesce(r2.review_count, 0) > 0
        then round(
            (coalesce(r2.promoters, 0) - coalesce(r2.detractors, 0))::double
            / r2.review_count * 100, 1)
        else null
    end as nps_score
from flights f
left join bookings_agg  b  on f.flight_id = b.flight_id
left join reviews_agg   r2 on f.flight_id = r2.flight_id
left join {{ ref('dim_route') }} r on f.route_id = r.route_id
