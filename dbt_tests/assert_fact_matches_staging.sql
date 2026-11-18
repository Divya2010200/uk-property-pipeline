-- Returns a row if the fact table gained or lost sales or money.
with staging as (
    select count(*) as sales, sum(price) as total_price
    from {{ ref('stg_price_paid') }}
),

fact as (
    select count(*) as sales, sum(price) as total_price
    from {{ ref('fct_sales') }}
)

select staging.sales as staging_sales, fact.sales as fact_sales
from staging
cross join fact
where staging.sales <> fact.sales
   or staging.total_price <> fact.total_price
