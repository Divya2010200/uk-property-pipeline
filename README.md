# UK Property Data Pipeline

A batch data pipeline that turns HM Land Registry Price Paid Data into tested, analysis-ready tables.

For the 2025 file, it loads 992,278 property sales into a DuckDB warehouse and builds a star schema with dbt.

## Architecture

```
Airflow schedules and retries the following steps:

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

## Run it with Airflow

Docker Desktop is required.

```powershell
Invoke-WebRequest https://airflow.apache.org/docs/apache-airflow/3.4.0/docker-compose.yaml -OutFile docker-compose.yaml
New-Item -ItemType Directory -Force dags, logs, plugins, config
Set-Content .env "AIRFLOW_UID=50000", "AIRFLOW_IMAGE_NAME=uk-property-airflow:latest"
docker build -t uk-property-airflow:latest .
docker compose up airflow-init
docker compose up -d
```

Open http://localhost:8080, then enable and run `uk_property_pipeline`.

## Run it on BigQuery

The same dbt models also run on BigQuery in the London region, using the free sandbox.

```powershell
.venv\Scripts\python -m pip install -r requirements-bigquery.txt
gcloud.cmd auth application-default login
.venv\Scripts\python -m pipeline.load_bigquery --year 2025
.venv\Scripts\dbt build --target bigquery
.venv\Scripts\python -m pipeline.verify_bigquery
```

Sandbox tables expire after 60 days, so the pipeline may need to be run again.

## Current limitations

- Loads complete yearly files; monthly change and delete records are not applied yet
- Airflow runs locally and currently targets DuckDB
- Recent months may be incomplete because sales are registered after they happen

## Roadmap

- Incremental monthly updates
- Airflow-managed BigQuery runs

## Data source and licence

Contains HM Land Registry data © Crown copyright and database right 2021. This data is licensed under the Open Government Licence v3.0.
