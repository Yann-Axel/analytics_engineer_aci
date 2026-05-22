{#-
    Customer-level KPIs + derived business segments used by retention and
    upsell decisions. Thresholds are calibrated against the actual revenue
    distribution: p33 ≈ $13K, p80 ≈ $17.6K.

    Thresholds are defined as dbt vars in dbt_project.yml so they can be
    re-tuned without code changes.
-#}
with cv as (
    select * from {{ ref('fact_customer_value') }}
),
reviews as (
    select
        fb.customer_id,
        avg(sr.nps_score)    as avg_nps,
        count(sr.review_id)  as review_count
    from {{ ref('stg_reviews') }} sr
    join {{ ref('fact_booking') }} fb on sr.flight_id = fb.flight_id
    group by fb.customer_id
)
select
    cv.customer_id,
    cv.full_name,
    cv.customer_segment,
    cv.loyalty_tier,
    cv.loyalty_tier_rank,
    cv.tenure_months,
    cv.total_flights,
    cv.total_revenue_usd,
    cv.annualized_revenue_usd,
    cv.avg_revenue_per_booking,
    cv.total_ancillary_usd,
    cv.ancillary_attach_rate_pct,
    cv.premium_conversion_rate_pct,
    cv.booking_frequency_per_month,
    cv.days_since_last_booking,
    cv.churn_risk_label,
    cv.distinct_routes_flown,
    cv.max_points_balance,
    cv.total_points_earned,
    cv.total_support_tickets,
    cv.avg_csat_score,
    coalesce(r.avg_nps, 5)      as avg_nps_given,
    coalesce(r.review_count, 0) as review_count,

    {#- Value tier: percentile-calibrated thresholds (p33 / p80). -#}
    case
        when cv.total_revenue_usd >= {{ var('value_tier_high_threshold') }} then 'High Value'
        when cv.total_revenue_usd >= {{ var('value_tier_mid_threshold')  }} then 'Mid Value'
        else 'Low Value'
    end as value_tier,

    {#- Upsell propensity: premium conversion OR top loyalty tiers OR
        active ancillary buyers (>50% attach + >=35 flights). -#}
    case
        when cv.premium_conversion_rate_pct > 15
            or cv.loyalty_tier_rank >= 3
        then 'High Propensity'
        when cv.total_flights >= 35
            and cv.ancillary_attach_rate_pct > 50
        then 'Medium Propensity'
        else 'Low Propensity'
    end as upsell_propensity,

    {#- Retention action: tercile of flight frequency relative to peers.
        Days-based recency is also available via cv.churn_risk_label but in
        the current single-month snapshot, frequency is the stronger signal. -#}
    case
        when cv.total_flights < 30 then 'Priority Retain'
        when cv.total_flights < 37 then 'Retain'
        else 'Maintain'
    end as retention_action

from cv
left join reviews r on cv.customer_id = r.customer_id
