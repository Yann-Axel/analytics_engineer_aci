{#-
    Cross-sectional KPIs by route_type × haul_category.

    With only a single calendar month of data, a literal "monthly time
    series" has one row per route type and provides little signal. This
    table is therefore framed as a cross-section: how the network performs
    across Domestic / Regional / International, useful for the executive
    summary and the dashboard's "by route type" comparisons.

    All flights are included (no cancellation filter) so cancellation_rate
    remains a comparable KPI.
-#}
select
    r.route_type,
    r.haul_category,
    count(f.flight_id)                  as total_flights,
    count(distinct f.route_id)          as distinct_routes,
    sum(f.booked_seats)                 as total_pax,
    avg(f.load_factor_pct)              as avg_load_factor_pct,
    avg(f.delay_min)                    as avg_delay_min,
    round(
        sum(case when f.flight_status = 'Cancelled' then 1 else 0 end)::double
        / nullif(count(f.flight_id), 0) * 100, 1) as cancellation_rate_pct,
    round(
        sum(case when f.delay_category in ('Moderate Delay', 'Major Delay') then 1 else 0 end)::double
        / nullif(count(f.flight_id), 0) * 100, 1) as delay_rate_pct,
    sum(f.total_revenue_usd)            as total_revenue_usd,
    sum(f.ticket_revenue_usd)           as ticket_revenue_usd,
    sum(f.ancillary_revenue_usd)        as ancillary_revenue_usd,
    avg(f.avg_ticket_price_usd)         as avg_ticket_price_usd,
    sum(f.estimated_margin_usd)         as total_margin_usd,
    round(
        sum(f.estimated_margin_usd) / nullif(sum(f.total_revenue_usd), 0) * 100,
    1) as margin_pct,
    avg(f.nps_score)                    as avg_nps_score
from {{ ref('fact_flight') }} f
join {{ ref('dim_route') }} r on f.route_id = r.route_id
group by r.route_type, r.haul_category
order by total_revenue_usd desc
