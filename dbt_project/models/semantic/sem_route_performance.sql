{#-
    Route-level KPI table — the canonical semantic record per route used by
    the dashboard, the MCP server, and the ontology layer.

    Contains 25+ KPIs covering:
      * commercial: revenue, margin, yield, avg ticket price
      * capacity:   load factor, breakeven load factor
      * operations: delay rate, cancellation rate
      * customer:   NPS, support_ticket_count, avg_support_csat
      * competitive: aci_avg_price, competitor_avg_price, price gap
-#}
with flights as (
    select * from {{ ref('fact_flight') }}
),
routes as (
    select * from {{ ref('dim_route') }}
),
competitor as (
    select
        route_id,
        avg(aci_avg_price_usd)        as aci_avg_price,
        avg(competitor_avg_price_usd) as competitor_avg_price,
        avg(price_gap_usd)            as avg_price_gap
    from synth_competitor_context
    group by route_id
),
tickets as (
    select
        route_id,
        count(*)          as total_tickets,
        sum(is_resolved)  as resolved_tickets,
        avg(csat_score)   as avg_csat
    from {{ ref('stg_support_tickets') }}
    group by route_id
)
select
    r.route_id,
    r.route_label,
    r.route_type,
    r.haul_category,
    r.distance_km,
    r.origin_airport_code,
    r.destination_airport_code,
    r.origin_city,
    r.destination_city,
    r.seat_capacity            as configured_seats,
    r.total_operating_cost_usd as cost_per_flight_usd,
    r.breakeven_load_factor_pct,
    r.avg_competitor_price_usd,

    count(f.flight_id)                                                                             as total_flights,
    sum(case when f.flight_status = 'Cancelled' then 1 else 0 end)                                 as cancelled_flights,
    sum(case when f.delay_category in ('Moderate Delay', 'Major Delay') then 1 else 0 end)         as significant_delays,
    round(
        sum(case when f.flight_status = 'Cancelled' then 1 else 0 end)::double
        / nullif(count(f.flight_id), 0) * 100, 1)                                                  as cancellation_rate_pct,
    round(
        sum(case when f.delay_category in ('Moderate Delay', 'Major Delay') then 1 else 0 end)::double
        / nullif(count(f.flight_id), 0) * 100, 1)                                                  as delay_rate_pct,
    avg(f.delay_min)                                                                               as avg_delay_min,

    sum(f.total_revenue_usd)                          as total_revenue_usd,
    sum(f.ticket_revenue_usd)                         as ticket_revenue_usd,
    sum(f.ancillary_revenue_usd)                      as ancillary_revenue_usd,
    avg(f.avg_ticket_price_usd)                       as avg_ticket_price_usd,
    sum(f.estimated_margin_usd)                       as total_margin_usd,
    round(
        sum(f.estimated_margin_usd) / nullif(sum(f.total_revenue_usd), 0) * 100,
    1) as margin_pct,

    avg(f.load_factor_pct) as avg_load_factor_pct,
    min(f.load_factor_pct) as min_load_factor_pct,
    max(f.load_factor_pct) as max_load_factor_pct,

    sum(f.booked_seats)  as total_pax,
    sum(f.premium_pax)   as total_premium_pax,
    round(sum(f.premium_pax)::double / nullif(sum(f.booked_seats), 0) * 100, 1) as premium_pax_rate_pct,

    avg(f.ancillary_attach_rate_pct) as avg_ancillary_attach_rate_pct,

    avg(f.nps_score)         as avg_nps_score,
    sum(f.review_count)      as total_reviews,
    sum(f.promoter_count)    as total_promoters,
    sum(f.detractor_count)   as total_detractors,
    round(
        (sum(f.promoter_count) - sum(f.detractor_count))::double
        / nullif(sum(f.review_count), 0) * 100, 1) as route_nps,

    c.aci_avg_price,
    c.competitor_avg_price,
    c.avg_price_gap,
    case when c.avg_price_gap > 0 then 'Premium' else 'Discounted' end as pricing_position,

    coalesce(t.total_tickets, 0) as support_ticket_count,
    t.avg_csat                   as avg_support_csat,

    round(
        sum(f.total_revenue_usd) / nullif(sum(f.booked_seats) * r.distance_km, 0) * 100,
    4) as yield_cents_per_pax_km

from flights f
join routes r on f.route_id = r.route_id
left join competitor c on r.route_id = c.route_id
left join tickets    t on r.route_id = t.route_id
group by
    r.route_id, r.route_label, r.route_type, r.haul_category, r.distance_km,
    r.origin_airport_code, r.destination_airport_code, r.origin_city,
    r.destination_city, r.seat_capacity, r.total_operating_cost_usd,
    r.breakeven_load_factor_pct, r.avg_competitor_price_usd,
    c.aci_avg_price, c.competitor_avg_price, c.avg_price_gap,
    t.total_tickets, t.avg_csat
