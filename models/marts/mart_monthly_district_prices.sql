-- Standard (category A) sales only: category B includes transfers such as
-- repossessions and sales to companies, which distort typical prices.
select
    dates.month_start,
    locations.county,
    locations.district,
    count(*) as sales_count,
    cast(median(sales.price) as bigint) as median_price,
    cast(avg(sales.price) as bigint) as average_price,
    min(sales.price) as lowest_price,
    max(sales.price) as highest_price
from {{ ref('fct_sales') }} as sales
inner join {{ ref('dim_date') }} as dates
    on sales.date_key = dates.date_key
inner join {{ ref('dim_location') }} as locations
    on sales.location_key = locations.location_key
where sales.ppd_category = 'A'
group by 1, 2, 3
