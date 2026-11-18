"""Check that the BigQuery tables match the local DuckDB warehouse."""

from __future__ import annotations

import argparse
import os

import duckdb

from pipeline.load_bigquery import DEFAULT_PROJECT, LOCATION

MEDIAN_TOLERANCE = 1

MART_COLUMNS = "month_start, county, district, sales_count, median_price"


def index_mart(rows):
    return {(row[0], row[1], row[2]): (int(row[3]), int(row[4])) for row in rows}


def compare_marts(local_rows, cloud_rows) -> list[str]:
    local = index_mart(local_rows)
    cloud = index_mart(cloud_rows)
    problems = []
    if local.keys() != cloud.keys():
        problems.append(f"different areas: DuckDB {len(local):,}, BigQuery {len(cloud):,}")
    for key in local.keys() & cloud.keys():
        local_sales, local_median = local[key]
        cloud_sales, cloud_median = cloud[key]
        if local_sales != cloud_sales or abs(local_median - cloud_median) > MEDIAN_TOLERANCE:
            problems.append(f"{key}: DuckDB {local[key]}, BigQuery {cloud[key]}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT", DEFAULT_PROJECT))
    args = parser.parse_args()

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project, location=LOCATION)
    fact_sql = "SELECT count(*), sum(price) FROM {}"
    mart_sql = f"SELECT {MART_COLUMNS} FROM {{}}"

    with duckdb.connect("data/warehouse.duckdb", read_only=True) as connection:
        local_fact = tuple(connection.execute(fact_sql.format("analytics.fct_sales")).fetchone())
        local_mart = connection.execute(
            mart_sql.format("analytics.mart_monthly_district_prices")
        ).fetchall()

    prefix = f"`{args.project}.analytics"
    cloud_fact = tuple(next(iter(client.query(fact_sql.format(f"{prefix}.fct_sales`")).result())).values())
    cloud_mart = [
        tuple(row.values())
        for row in client.query(mart_sql.format(f"{prefix}.mart_monthly_district_prices`")).result()
    ]

    print(f"DuckDB:   {local_fact[0]:,} sales, GBP {local_fact[1]:,}")
    print(f"BigQuery: {cloud_fact[0]:,} sales, GBP {cloud_fact[1]:,}")
    if local_fact != cloud_fact:
        raise SystemExit("FACT TOTALS DO NOT MATCH")

    problems = compare_marts(local_mart, cloud_mart)
    if problems:
        raise SystemExit(f"{len(problems)} mart differences, first: {problems[0]}")
    print(f"Monthly mart matches across {len(local_mart):,} rows")


if __name__ == "__main__":
    main()
