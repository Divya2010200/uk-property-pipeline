{% macro surrogate_key(columns) -%}
{%- if target.type == 'bigquery' -%}
to_hex(md5(concat({% for column in columns %}{% if not loop.first %}, '|', {% endif %}coalesce(cast({{ column }} as string), ''){% endfor %})))
{%- else -%}
md5(concat_ws('|'{% for column in columns %}, coalesce(cast({{ column }} as varchar), ''){% endfor %}))
{%- endif -%}
{%- endmacro %}
