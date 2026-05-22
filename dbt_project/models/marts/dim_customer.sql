with customers as (
    select * from {{ ref('stg_customers') }}
),
loyalty_summary as (
    select
        customer_id,
        sum(case when is_earn   = 1 then points_change else 0 end) as total_points_earned,
        sum(case when is_redeem = 1 then abs(points_change) else 0 end) as total_points_redeemed,
        max(running_balance) as max_points_balance,
        count(*) as loyalty_event_count,
        max(activity_date) as last_loyalty_date
    from {{ ref('stg_loyalty') }}
    group by customer_id
),
ticket_summary as (
    select
        customer_id,
        count(*) as total_tickets,
        sum(is_resolved) as resolved_tickets,
        avg(csat_score)  as avg_csat_score
    from {{ ref('stg_support_tickets') }}
    group by customer_id
)
select
    c.customer_id,
    c.full_name,
    c.gender,
    c.birth_date,
    c.age_years,
    c.country,
    c.city,
    c.customer_segment,
    c.loyalty_tier,
    c.loyalty_tier_rank,
    c.signup_date,
    c.tenure_months,
    c.preferred_channel,
    coalesce(l.total_points_earned, 0)    as total_points_earned,
    coalesce(l.total_points_redeemed, 0)  as total_points_redeemed,
    coalesce(l.max_points_balance, 0)     as max_points_balance,
    coalesce(l.loyalty_event_count, 0)    as loyalty_event_count,
    l.last_loyalty_date,
    coalesce(t.total_tickets, 0)          as total_support_tickets,
    coalesce(t.resolved_tickets, 0)       as resolved_support_tickets,
    t.avg_csat_score
from customers c
left join loyalty_summary l on c.customer_id = l.customer_id
left join ticket_summary  t on c.customer_id = t.customer_id
