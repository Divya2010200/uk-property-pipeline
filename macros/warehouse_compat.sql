{# Small differences between DuckDB and BigQuery SQL live here. #}

{% macro date_key(column) -%}
{%- if target.type == 'bigquery' -%}
cast(format_date('%Y%m%d', {{ column }}) as int64)
{%- else -%}
cast(strftime({{ column }}, '%Y%m%d') as integer)
{%- endif -%}
{%- endmacro %}

{% macro first_word(column) -%}
{%- if target.type == 'bigquery' -%}
split({{ column }}, ' ')[safe_offset(0)]
{%- else -%}
split_part({{ column }}, ' ', 1)
{%- endif -%}
{%- endmacro %}

{% macro month_start(column) -%}
{%- if target.type == 'bigquery' -%}
date_trunc({{ column }}, month)
{%- else -%}
cast(date_trunc('month', {{ column }}) as date)
{%- endif -%}
{%- endmacro %}

{% macro month_name(column) -%}
{%- if target.type == 'bigquery' -%}
format_date('%B', {{ column }})
{%- else -%}
monthname({{ column }})
{%- endif -%}
{%- endmacro %}

{% macro day_name(column) -%}
{%- if target.type == 'bigquery' -%}
format_date('%A', {{ column }})
{%- else -%}
dayname({{ column }})
{%- endif -%}
{%- endmacro %}

{% macro iso_day_of_week(column) -%}
{%- if target.type == 'bigquery' -%}
mod(extract(dayofweek from {{ column }}) + 5, 7) + 1
{%- else -%}
isodow({{ column }})
{%- endif -%}
{%- endmacro %}
