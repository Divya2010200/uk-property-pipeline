select distinct
    property_key,
    property_type_code,
    property_type,
    old_new_code,
    is_new_build,
    duration_code,
    tenure
from {{ ref('stg_price_paid') }}
