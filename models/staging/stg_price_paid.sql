with source as (

    select * from {{ source('land_registry', 'price_paid') }}

),

cleaned as (

    select
        trim(transaction_id, '{}') as transaction_id,
        cast(price as bigint) as price,
        cast(substr(transfer_date, 1, 10) as date) as transfer_date,
        nullif(upper(trim(postcode)), '') as postcode,
        upper(trim(property_type)) as property_type_code,
        upper(trim(old_new)) as old_new_code,
        upper(trim(duration)) as duration_code,
        nullif(upper(trim(locality)), '') as locality,
        nullif(upper(trim(town_city)), '') as town_city,
        nullif(upper(trim(district)), '') as district,
        nullif(upper(trim(county)), '') as county,
        upper(trim(ppd_category)) as ppd_category,
        upper(trim(record_status)) as record_status,
        source_file,
        loaded_at
    from source

),

deduplicated as (

    select *
    from cleaned
    qualify row_number() over (
        partition by transaction_id
        order by loaded_at desc, source_file desc
    ) = 1

),

final as (

    select
        transaction_id,
        price,
        transfer_date,
        cast(strftime(transfer_date, '%Y%m%d') as integer) as date_key,
        postcode,
        split_part(postcode, ' ', 1) as postcode_district,
        nullif(regexp_extract(postcode, '^[A-Z]+'), '') as postcode_area,
        locality,
        town_city,
        district,
        county,
        county = 'GREATER LONDON' as is_greater_london,
        property_type_code,
        case property_type_code
            when 'D' then 'Detached'
            when 'S' then 'Semi-detached'
            when 'T' then 'Terraced'
            when 'F' then 'Flat or maisonette'
            when 'O' then 'Other'
        end as property_type,
        old_new_code,
        old_new_code = 'Y' as is_new_build,
        duration_code,
        case duration_code
            when 'F' then 'Freehold'
            when 'L' then 'Leasehold'
            else 'Unknown'
        end as tenure,
        ppd_category,
        record_status,
        source_file,
        loaded_at,
        {{ surrogate_key(['postcode', 'locality', 'town_city', 'district', 'county']) }} as location_key,
        {{ surrogate_key(['property_type_code', 'old_new_code', 'duration_code']) }} as property_key
    from deduplicated

)

select * from final
