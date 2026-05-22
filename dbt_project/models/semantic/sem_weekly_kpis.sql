{#-
    Weekly time-series of route operations. The starter data covers a single
    calendar month (Jan 2025), so a weekly grain gives 4–5 points per route
    which is the minimum needed for trend lines on the dashboard.

    Cancellations are NOT filtered out — cancellation_rate_pct is itself a
    KPI we want to track at the weekly grain.
-#}
select
    strftime(flight_date, '%Y-W%W')             as year_week,
    date_trunc('week', flight_date)             as week_start,
    route_id,
    count(flight_id)                            as total_flights,
    sum(booked_seats)                           as total_pax,
    avg(load_factor_pct)                        as avg_load_factor_pct,
    avg(delay_min)                              as avg_delay_min,
    round(
        sum(case when flight_status = 'Cancelled' then 1 else 0 end)::double
        / nullif(count(flight_id), 0) * 100, 1) as cancellation_rate_pct,
    round(
        sum(case when delay_category in ('Moderate Delay', 'Major Delay') then 1 else 0 end)::double
        / nullif(count(flight_id), 0) * 100, 1) as delay_rate_pct,
    sum(total_revenue_usd)                      as total_revenue_usd,
    sum(estimated_margin_usd)                   as total_margin_usd,
    avg(nps_score)                              as avg_nps_score
from {{ ref('fact_flight') }}
group by year_week, week_start, route_id
order by week_start, route_id
