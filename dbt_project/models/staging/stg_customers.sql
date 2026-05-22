{#-
    Cleans raw_customers and derives age / tenure relative to the project's
    frozen reference date (see aci_config.py + dbt_project.yml). Using
    CURRENT_DATE here would let analytical aging drift with the calendar.

    The starter data uses an Explorer / Silver / Gold tier structure (no
    Platinum, ~40% of customers have no tier yet). Customers without a
    tier are surfaced as 'None' rather than silently bucketed as Bronze.
-#}
with source as (
    select * from raw_customers
)
select
    customer_id,
    first_name,
    last_name,
    first_name || ' ' || last_name as full_name,
    gender,
    try_cast(birth_date as date) as birth_date,
    date_diff('year', try_cast(birth_date as date), date '{{ var("reference_date") }}') as age_years,
    country,
    city,
    customer_segment,
    coalesce(nullif(trim(loyalty_tier), ''), 'None') as loyalty_tier,
    try_cast(signup_date as date) as signup_date,
    date_diff('month', try_cast(signup_date as date), date '{{ var("reference_date") }}') as tenure_months,
    preferred_channel,
    case coalesce(nullif(trim(loyalty_tier), ''), 'None')
        when 'Platinum' then 4
        when 'Gold'     then 3
        when 'Silver'   then 2
        when 'Explorer' then 1
        else 0
    end as loyalty_tier_rank
from source
