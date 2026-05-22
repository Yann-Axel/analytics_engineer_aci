{#-
    Customer ontology — five mutually exclusive classes that drive
    retention, upsell, and re-engagement decisions.

    Classes:
      * High-Value At-Risk — High Value tier AND below-median flight count
      * Loyal Advocate     — Gold/Platinum AND high flight count AND Maintain
      * Growth Target      — Mid/High Value AND propensity AND Maintain
      * Dormant            — fewer than 20 flights (never really engaged)
      * Casual             — fallback

    "At risk" is defined as flight-frequency-below-peer-median rather than
    days-since-last-booking. The starter data is a one-month snapshot, so
    recency would label every customer the same — frequency vs peers
    surfaces the real signal.

    ltv_potential_score (0–100) is an additive composite:
      value_tier (40) + loyalty_rank (20) + upsell_propensity (20) + churn (20)
-#}
with segments as (
    select * from {{ ref('sem_customer_segments') }}
)
select
    customer_id,
    full_name,
    customer_segment,
    loyalty_tier,
    value_tier,
    churn_risk_label,
    upsell_propensity,
    retention_action,
    total_revenue_usd,
    annualized_revenue_usd,
    total_flights,
    days_since_last_booking,
    loyalty_tier_rank,
    max_points_balance,
    ancillary_attach_rate_pct,
    premium_conversion_rate_pct,
    total_support_tickets,
    avg_nps_given,

    {#- ── Ontology attributes (boolean properties) ── -#}
    (value_tier = 'High Value')                             as is_high_value,
    (total_flights < 36
     or (total_flights < 39 and loyalty_tier_rank = 1))     as is_at_risk,
    (loyalty_tier_rank >= 3 and total_flights >= 39)        as is_loyalty_advocate,
    (upsell_propensity in ('High Propensity', 'Medium Propensity')
     and value_tier != 'Low Value')                         as is_upsell_target,
    (total_flights < 20)                                    as is_dormant,
    (total_support_tickets > 3
     and total_flights > 0
     and total_support_tickets::double / total_flights > 0.4) as is_high_complaint_rate,

    {#- ── Primary class (priority-ordered) ── -#}
    case
        when value_tier = 'High Value'
             and total_flights < 36
        then 'High-Value At-Risk'

        when loyalty_tier_rank >= 3
             and total_flights >= 39
             and retention_action = 'Maintain'
        then 'Loyal Advocate'

        when value_tier in ('Mid Value', 'High Value')
             and upsell_propensity in ('High Propensity', 'Medium Propensity')
             and retention_action = 'Maintain'
        then 'Growth Target'

        when total_flights < 20
        then 'Dormant'

        else 'Casual'
    end as customer_class,

    {#- ── Recommended action (mirrors class) ── -#}
    case
        when value_tier = 'High Value'
             and total_flights < 36
        then 'Priority retention offer: upgrade voucher or bonus miles'

        when loyalty_tier_rank >= 3
             and total_flights >= 39
             and retention_action = 'Maintain'
        then 'Reward and cross-sell: partner offers, ancillary upgrades'

        when value_tier in ('Mid Value', 'High Value')
             and upsell_propensity in ('High Propensity', 'Medium Propensity')
        then 'Upsell campaign: premium cabin trial, seat upgrade offer'

        when total_flights < 20
        then 'Re-engagement: targeted reactivation discount'

        else 'Nurture: standard loyalty communications'
    end as recommended_action,

    {#- LTV potential score (0–100). -#}
    least(100, round(
        (case when value_tier = 'High Value' then 40
              when value_tier = 'Mid Value'  then 20
              else 5 end)
        + (case when loyalty_tier_rank = 4 then 20
                when loyalty_tier_rank = 3 then 15
                when loyalty_tier_rank = 2 then 10
                else 0 end)
        + (case when upsell_propensity = 'High Propensity'   then 20
                when upsell_propensity = 'Medium Propensity' then 10
                else 0 end)
        + (case when churn_risk_label = 'Low Risk' then 20 else 0 end)
    )) as ltv_potential_score

from segments
