"""Print a short summary from the finished warehouse tables."""

import duckdb

QUERY = """
SELECT
    l.district,
    count(*) AS sales,
    cast(median(s.price) AS BIGINT) AS median_price
FROM analytics.fct_sales AS s
JOIN analytics.dim_location AS l USING (location_key)
WHERE s.ppd_category = 'A' AND l.is_greater_london
GROUP BY l.district
HAVING count(*) >= 100
ORDER BY median_price DESC
LIMIT 5
"""


def main() -> None:
    with duckdb.connect("data/warehouse.duckdb", read_only=True) as connection:
        for table in ["fct_sales", "dim_location", "dim_property", "dim_date"]:
            count = connection.execute(f"SELECT count(*) FROM analytics.{table}").fetchone()[0]
            print(f"{table}: {count:,} rows")

        print("\nHighest median prices in Greater London (standard sales):")
        for district, sales, price in connection.execute(QUERY).fetchall():
            print(f"{district}: GBP {price:,} from {sales:,} sales")


if __name__ == "__main__":
    main()
