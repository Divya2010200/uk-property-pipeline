-- Returns a row if the monthly mart does not add up to its standard sales.
with fact as (
    select count(*) as sales
    from {{ ref('fct_sales') }}
    where ppd_category = 'A'
),

mart as (
    select sum(sales_count) as sales
    from {{ ref('mart_monthly_district_prices') }}
)

select fact.sales as fact_sales, mart.sales as mart_sales
from fact
cross join mart
where fact.sales <> mart.sales
