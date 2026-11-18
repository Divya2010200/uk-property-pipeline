select distinct
    location_key,
    postcode,
    postcode_district,
    postcode_area,
    locality,
    town_city,
    district,
    county,
    is_greater_london
from {{ ref('stg_price_paid') }}
