-- Date dimension covering the full data range
with date_spine as (
    select
        range::date as date_day
    from range(date '2024-11-01', date '2026-01-01', interval '1 day')
)
select
    date_day,
    strftime(date_day, '%Y%m%d')::integer as date_key,
    date_part('year', date_day)    as year,
    date_part('quarter', date_day) as quarter,
    date_part('month', date_day)   as month,
    date_part('week', date_day)    as week_of_year,
    date_part('day', date_day)     as day_of_month,
    date_part('dow', date_day)     as day_of_week,
    strftime(date_day, '%B')       as month_name,
    strftime(date_day, '%Y-%m')    as year_month,
    'Q' || date_part('quarter', date_day) || ' ' || date_part('year', date_day) as quarter_label,
    date_day >= date '2025-01-01' as is_2025,
    date_part('dow', date_day) in (0, 6) as is_weekend
from date_spine
