with source as (
    select * from synth_customer_reviews
)
select
    review_id,
    flight_id,
    route_id,
    try_cast(review_date as date) as review_date,
    cast(nps_score as integer) as nps_score,
    sentiment,
    review_text,
    language,
    source,
    case
        when cast(nps_score as integer) >= 9 then 'Promoter'
        when cast(nps_score as integer) >= 7 then 'Passive'
        else 'Detractor'
    end as nps_category,
    length(review_text) as review_length
from source
