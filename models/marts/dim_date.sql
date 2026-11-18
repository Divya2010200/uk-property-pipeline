with bounds as (

    select
        cast(date_trunc('year', min(transfer_date)) as timestamp) as first_day,
        cast(date_trunc('year', max(transfer_date)) + interval '1 year' - interval '1 day' as timestamp) as last_day
    from {{ ref('stg_price_paid') }}

),

days as (

    select cast(unnest(generate_series(first_day, last_day, interval '1 day')) as date) as date_day
    from bounds

)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day,
    year(date_day) as year,
    quarter(date_day) as quarter,
    month(date_day) as month,
    monthname(date_day) as month_name,
    cast(date_trunc('month', date_day) as date) as month_start,
    isodow(date_day) as day_of_week,
    dayname(date_day) as day_name,
    isodow(date_day) in (6, 7) as is_weekend
from days
