"""Monthly orchestration of the UK property pipeline."""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

PROJECT_DIR = "/opt/project"
PYTHON = "/opt/pipeline-venv/bin/python"
DBT = "/opt/pipeline-venv/bin/dbt"

with DAG(
    dag_id="uk_property_pipeline",
    description="Load Land Registry sales, build dbt models and verify the results",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 5 * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    params={"year": Param(2025, type="integer", minimum=1995)},
    tags=["property", "dbt", "duckdb"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_price_paid",
        bash_command=f"{PYTHON} -m pipeline.ingest --year {{{{ params.year }}}}",
        cwd=PROJECT_DIR,
    )

    build_models = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT} build",
        cwd=PROJECT_DIR,
    )

    sanity_check = BashOperator(
        task_id="sanity_check",
        bash_command=f"{PYTHON} -m pipeline.sanity_check",
        cwd=PROJECT_DIR,
    )

    ingest >> build_models >> sanity_check
