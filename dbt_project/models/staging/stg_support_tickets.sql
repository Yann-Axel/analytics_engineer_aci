with source as (
    select * from synth_support_tickets
)
select
    ticket_id,
    customer_id,
    route_id,
    try_cast(open_date as date) as open_date,
    category,
    description,
    sentiment,
    status,
    try_cast(nullif(cast(resolution_days as varchar), '') as integer) as resolution_days,
    try_cast(nullif(cast(csat_score as varchar), '')     as integer) as csat_score,
    case when status = 'Resolved' then 1 else 0 end as is_resolved,
    case
        when category in ('Baggage', 'Flight Delay') then 'Operational'
        when category in ('Customer Service', 'Refund') then 'Commercial'
        else 'Product'
    end as ticket_domain
from source
