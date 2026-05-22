with source as (
    select * from synth_loyalty_activity
)
select
    activity_id,
    customer_id,
    try_cast(activity_date as date) as activity_date,
    activity_type,
    cast(points_change      as integer) as points_change,
    cast(running_balance    as integer) as running_balance,
    tier_after,
    channel,
    case when cast(points_change as integer) > 0 then 1 else 0 end as is_earn,
    case when cast(points_change as integer) < 0 then 1 else 0 end as is_redeem
from source
