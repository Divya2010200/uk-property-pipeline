"""Compare finished tables with the raw data and show monthly volumes."""

import duckdb

DISTRICT = "KENSINGTON AND CHELSEA"


def main() -> None:
    with duckdb.connect("data/warehouse.duckdb", read_only=True) as connection:
        raw = connection.execute(
            "SELECT count(*), sum(cast(price AS BIGINT)) FROM raw.price_paid"
        ).fetchone()
        fact = connection.execute(
            "SELECT count(*), sum(price) FROM analytics.fct_sales"
        ).fetchone()
        print(f"Raw:  {raw[0]:,} sales, GBP {raw[1]:,}")
        print(f"Fact: {fact[0]:,} sales, GBP {fact[1]:,}")
        if raw != fact:
            raise SystemExit("TOTALS DO NOT MATCH")
        print("Totals match")

        median_from_raw = connection.execute(
            """
            SELECT cast(median(cast(price AS BIGINT)) AS BIGINT), count(*)
            FROM raw.price_paid
            WHERE upper(trim(district)) = ?
              AND upper(trim(county)) = 'GREATER LONDON'
              AND upper(trim(ppd_category)) = 'A'
            """,
            [DISTRICT],
        ).fetchone()
        print(
            f"\n{DISTRICT} from raw data: median GBP {median_from_raw[0]:,} "
            f"from {median_from_raw[1]:,} sales"
        )

        print("\nSales by month:")
        months = connection.execute(
            """
            SELECT
                strftime(d.month_start, '%Y-%m') AS month,
                count(*) AS all_sales,
                count(*) FILTER (WHERE s.ppd_category = 'A') AS standard_sales
            FROM analytics.fct_sales AS s
            JOIN analytics.dim_date AS d USING (date_key)
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
        for month, all_sales, standard_sales in months:
            print(f"{month}: {all_sales:,} total, {standard_sales:,} standard")


if __name__ == "__main__":
    main()
