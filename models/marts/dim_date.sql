with

{% if target.type == 'bigquery' %}

bounds as (

    select
        date_trunc(min(transfer_date), year) as first_day,
        date_sub(date_add(date_trunc(max(transfer_date), year), interval 1 year), interval 1 day) as last_day
    from {{ ref('stg_price_paid') }}

),

days as (

    select date_day
    from bounds
    cross join unnest(generate_date_array(first_day, last_day)) as date_day

)

{% else %}

bounds as (

    select
        cast(date_trunc('year', min(transfer_date)) as timestamp) as first_day,
        cast(date_trunc('year', max(transfer_date)) + interval '1 year' - interval '1 day' as timestamp) as last_day
    from {{ ref('stg_price_paid') }}

),

days as (

    select cast(unnest(generate_series(first_day, last_day, interval '1 day')) as date) as date_day
    from bounds

)

{% endif %}

select
    {{ date_key('date_day') }} as date_key,
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    {{ month_name('date_day') }} as month_name,
    {{ month_start('date_day') }} as month_start,
    {{ iso_day_of_week('date_day') }} as day_of_week,
    {{ day_name('date_day') }} as day_name,
    {{ iso_day_of_week('date_day') }} in (6, 7) as is_weekend
from days
