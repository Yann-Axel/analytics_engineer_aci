{#-
    Route ontology — classifies each route into one of six business classes
    and derives a budget recommendation. Multi-signal inference combines
    profitability (margin_pct), operations (delay_rate, cancellation_rate),
    and satisfaction (route_nps).

    Classes (mutually exclusive, evaluated in order):
      * Strategic Growth        — profitable AND reliable
      * Operational Risk        — profitable BUT operationally stressed
      * Cash Cow                — profitable, moderate ops
      * Critical Underperformer — weak margin AND ops failures (double problem)
      * Underperforming         — weak margin, ops OK
      * Monitor                 — fallback

    Thresholds are calibrated to the Jan 2025 distribution (margin 14–64%,
    delay 3–30%, all load factors below breakeven). Adjusting them is the
    primary lever for tuning recommendations without changing the schema.

    classification_confidence_pct is metadata: it quantifies how much
    evidence (flights, reviews, tickets) supports the class assignment.
    A low confidence (<50) should trigger human review before acting.
-#}
with routes as (
    select * from {{ ref('sem_route_performance') }}
)
select
    route_id,
    route_label,
    route_type,
    haul_category,
    origin_city,
    destination_city,
    total_revenue_usd,
    total_margin_usd,
    margin_pct,
    avg_load_factor_pct,
    breakeven_load_factor_pct,
    delay_rate_pct,
    cancellation_rate_pct,
    route_nps,
    avg_price_gap,
    support_ticket_count,
    total_pax,

    {#- ── Ontology attributes (observed properties) ── -#}
    (margin_pct > 0)                                          as is_profitable,
    (delay_rate_pct > 20 or cancellation_rate_pct > 5)        as is_operationally_stressed,
    (route_nps > -15)                                         as is_high_satisfaction,
    (margin_pct > 40 and delay_rate_pct < 15)                 as has_scale_potential,
    (avg_load_factor_pct >= breakeven_load_factor_pct
     and (delay_rate_pct > 25 or cancellation_rate_pct > 5))  as is_demand_strong_ops_weak,

    {#- ── Primary class (priority-ordered CASE) ── -#}
    case
        when margin_pct >= 50
             and delay_rate_pct < 10
             and cancellation_rate_pct < 5
        then 'Strategic Growth'

        when margin_pct >= 40
             and (delay_rate_pct >= 20 or cancellation_rate_pct >= 5)
        then 'Operational Risk'

        when margin_pct >= 40
             and delay_rate_pct < 20
        then 'Cash Cow'

        when margin_pct < 20
             and (delay_rate_pct > 15 or cancellation_rate_pct > 5)
        then 'Critical Underperformer'

        when margin_pct < 25
        then 'Underperforming'

        else 'Monitor'
    end as route_class,

    {#- ── Budget recommendation (parallel to class) ── -#}
    case
        when margin_pct >= 50
             and delay_rate_pct < 10
             and cancellation_rate_pct < 5
        then 'Invest: expand frequency or upsell premium cabin'

        when margin_pct >= 40
             and (delay_rate_pct >= 20 or cancellation_rate_pct >= 5)
        then 'Fix Operations: reliability issues limiting revenue potential'

        when margin_pct >= 40
             and delay_rate_pct < 20
        then 'Protect: high-margin route — defend pricing and market share'

        when margin_pct < 20
             and (delay_rate_pct > 15 or cancellation_rate_pct > 5)
        then 'Restructure: poor margin + ops failures — review viability'

        when margin_pct < 25
        then 'Improve Revenue Mix: increase premium pax and ancillary'

        else 'Maintain: monitor for improvement opportunities'
    end as budget_recommendation,

    {#- Confidence score: how much evidence supports the classification.
        Caps at 100, base 20, scales with flights / reviews / tickets. -#}
    least(100, round(
        (case when total_flights >= 30 then 30 else total_flights end)
        + (case when total_reviews >= 20 then 30 else total_reviews * 1.5 end)
        + (case when support_ticket_count >= 10 then 20 else support_ticket_count * 2 end)
        + 20
    )) as classification_confidence_pct

from routes
