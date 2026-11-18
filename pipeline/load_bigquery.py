"""Load a validated Price Paid CSV into BigQuery.

The BigQuery sandbox has no DML, so each year is a separate table that a load
job replaces completely. A failed job leaves the previous table in place.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline.ingest import COLUMNS, IngestError, RAW_DIR, validate_csv

LOCATION = "europe-west2"
RAW_DATASET = "raw"
DEFAULT_PROJECT = "uk-property-pipeline"


def table_id(project: str, year: int) -> str:
    return f"{project}.{RAW_DATASET}.price_paid_{year}"


def load_file(client, bigquery, path: Path, destination: str, expected_rows: int) -> int:
    client.create_dataset(
        _dataset(bigquery, destination), exists_ok=True
    )
    config = bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(name, "STRING") for name in COLUMNS],
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        skip_leading_rows=0,
        field_delimiter=",",
        quote_character='"',
        encoding="UTF-8",
        max_bad_records=0,
    )
    with path.open("rb") as source:
        job = client.load_table_from_file(source, destination, job_config=config, location=LOCATION)
    job.result()

    loaded = int(job.output_rows)
    if loaded != expected_rows:
        raise IngestError(f"BigQuery loaded {loaded:,} rows but the file has {expected_rows:,}")
    return loaded


def _dataset(bigquery, destination: str):
    project, dataset, _ = destination.split(".")
    result = bigquery.Dataset(f"{project}.{dataset}")
    result.location = LOCATION
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT", DEFAULT_PROJECT))
    args = parser.parse_args()

    from google.cloud import bigquery

    path = RAW_DIR / f"pp-{args.year}.csv"
    if not path.exists():
        raise SystemExit(f"{path} is missing. Run pipeline.ingest first.")

    result = validate_csv(path, args.year)
    print(f"Validated {result.rows:,} rows: {result.bad_rows:,} bad")

    destination = table_id(args.project, args.year)
    client = bigquery.Client(project=args.project, location=LOCATION)
    loaded = load_file(client, bigquery, path, destination, result.rows)
    print(f"Loaded {loaded:,} rows into {destination}")


if __name__ == "__main__":
    main()
