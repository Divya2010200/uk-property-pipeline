# UK Property Data Pipeline

A batch data pipeline that turns HM Land Registry Price Paid Data into tested, analysis-ready tables.

For the 2025 file, it loads 992,278 property sales into a DuckDB warehouse and builds a star schema with dbt.

## Architecture

```
Land Registry CSV
      |
      v
Python ingestion      download, retry, validate, repeat-safe load
      |
      v
raw.price_paid        unchanged source data as text
      |
      v
dbt staging           types, cleaning, de-duplication
      |
      v
dbt star schema       fct_sales, dim_date, dim_location, dim_property
      |
      v
dbt mart              mart_monthly_district_prices
```

## Data quality

- Row structure, prices and dates are validated before loading
- A load is rolled back if its row count does not match the file
- 33 dbt tests check uniqueness, missing values, accepted codes, relationships and positive values
- Reconciliation tests confirm that sale counts and totals match between layers
- GitHub Actions runs the Python tests and the dbt build on a small synthetic sample

## Run it

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pipeline.ingest --year 2025
.venv\Scripts\dbt build
.venv\Scripts\python -m pipeline.summary
.venv\Scripts\python -m pipeline.sanity_check
```

## Current limitations

- Loads complete yearly files; monthly change and delete records are not applied yet
- Runs locally on DuckDB
- Recent months may be incomplete because sales are registered after they happen

## Roadmap

- Airflow orchestration
- Incremental monthly updates
- Optional cloud warehouse target

## Data source and licence

Contains HM Land Registry data © Crown copyright and database right 2021. This data is licensed under the Open Government Licence v3.0.
