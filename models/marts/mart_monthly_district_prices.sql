-- Standard (category A) sales only: category B includes transfers such as
-- repossessions and sales to companies, which distort typical prices.
with standard_sales as (

    select
        dates.month_start,
        locations.county,
        locations.district,
        sales.price
    from {{ ref('fct_sales') }} as sales
    inner join {{ ref('dim_date') }} as dates
        on sales.date_key = dates.date_key
    inner join {{ ref('dim_location') }} as locations
        on sales.location_key = locations.location_key
    where sales.ppd_category = 'A'

)

{% if target.type == 'bigquery' %}
{% set area = 'partition by month_start, county, district' %}
select distinct
    month_start,
    county,
    district,
    count(*) over ({{ area }}) as sales_count,
    cast(percentile_cont(price, 0.5) over ({{ area }}) as int64) as median_price,
    cast(avg(price) over ({{ area }}) as int64) as average_price,
    min(price) over ({{ area }}) as lowest_price,
    max(price) over ({{ area }}) as highest_price
from standard_sales
{% else %}
select
    month_start,
    county,
    district,
    count(*) as sales_count,
    cast(median(price) as bigint) as median_price,
    cast(avg(price) as bigint) as average_price,
    min(price) as lowest_price,
    max(price) as highest_price
from standard_sales
group by 1, 2, 3
{% endif %}
