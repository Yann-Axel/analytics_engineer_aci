{#-
    Clean airport reference data. ABJ (Abidjan) is the network hub; other
    Ivorian airports are flagged Domestic, the rest are International.
-#}
with source as (
    select * from raw_airports
)
select
    airport_code,
    airport_name,
    city,
    country,
    timezone,
    cast(latitude  as double) as latitude,
    cast(longitude as double) as longitude,
    case
        when airport_code = 'ABJ' then 'Hub'
        when country = 'Côte d''Ivoire' then 'Domestic'
        else 'International'
    end as airport_role
from source
