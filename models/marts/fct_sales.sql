select
    transaction_id,
    date_key,
    location_key,
    property_key,
    ppd_category,
    price
from {{ ref('stg_price_paid') }}
