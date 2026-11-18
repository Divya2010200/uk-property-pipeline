"""Download HM Land Registry Price Paid Data and load it into DuckDB.

Contains HM Land Registry data (c) Crown copyright and database right.
This data is licensed under the Open Government Licence v3.0.
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://price-paid-data.publicdata.landregistry.gov.uk"
RAW_DIR = Path("data/raw")
DEFAULT_DB = Path("data/warehouse.duckdb")
DEFAULT_YEAR = 2025
MAX_BAD_ROW_FRACTION = 0.001
CHUNK_SIZE = 1024 * 1024

# The published files have no header row, so the order here is the contract.
COLUMNS = [
    "transaction_id",
    "price",
    "transfer_date",
    "postcode",
    "property_type",
    "old_new",
    "duration",
    "paon",
    "saon",
    "street",
    "locality",
    "town_city",
    "district",
    "county",
    "ppd_category",
    "record_status",
]

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


class IngestError(RuntimeError):
    """The source data could not be downloaded or failed validation."""


@dataclass(frozen=True)
class ValidationResult:
    rows: int
    bad_rows: int
    outside_year: int


def file_url(year: int) -> str:
    return f"{BASE_URL}/pp-{year}.csv"


def download_file(
    url: str,
    destination: Path,
    *,
    force: bool = False,
    attempts: int = 3,
    backoff_seconds: float = 2.0,
    timeout: tuple[int, int] = (15, 120),
) -> bool:
    """Download url and return True, or return False if the file already exists.

    Data goes to a temporary file first, so an interrupted download can never
    be mistaken for a complete one.
    """
    if destination.exists() and not force:
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with requests.get(
                url,
                stream=True,
                timeout=timeout,
                headers={"Accept-Encoding": "identity"},
            ) as response:
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    raise IngestError(f"{url} returned HTTP {response.status_code}")
                response.raise_for_status()

                written = 0
                with partial.open("wb") as output:
                    for chunk in response.iter_content(CHUNK_SIZE):
                        output.write(chunk)
                        written += len(chunk)

                expected = response.headers.get("Content-Length")
                if expected is not None and written != int(expected):
                    raise requests.ConnectionError(
                        f"received {written} bytes, expected {expected}"
                    )

            partial.replace(destination)
            return True
        except (requests.RequestException, OSError) as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(backoff_seconds * 2 ** (attempt - 1))

    raise IngestError(f"could not download {url}: {last_error}")


def _row_is_valid(row: list[str]) -> bool:
    if len(row) != len(COLUMNS) or not row[0].strip():
        return False
    if not row[1].isdigit() or int(row[1]) <= 0:
        return False
    if not _ISO_DATE.match(row[2]):
        return False
    try:
        date.fromisoformat(row[2][:10])
    except ValueError:
        return False
    return True


def validate_csv(path: Path, year: int) -> ValidationResult:
    """Check the file's structure before anything is loaded."""
    rows = bad_rows = outside_year = 0
    prefix = f"{year}-"

    with path.open(encoding="utf-8", errors="replace", newline="") as source:
        for row in csv.reader(source):
            rows += 1
            if not _row_is_valid(row):
                bad_rows += 1
            elif not row[2].startswith(prefix):
                outside_year += 1

    if rows == 0:
        raise IngestError(f"{path} has no rows")
    if bad_rows / rows > MAX_BAD_ROW_FRACTION:
        raise IngestError(f"{path} has {bad_rows:,} bad rows out of {rows:,}")
    return ValidationResult(rows, bad_rows, outside_year)


def load_csv(path: Path, db_path: Path, expected_rows: int) -> int:
    """Replace this file's rows in raw.price_paid in one transaction.

    Every source column stays text here. Types and cleaning belong in dbt, so
    the raw table remains a faithful copy of what was published.
    """
    import duckdb

    db_path.parent.mkdir(parents=True, exist_ok=True)
    column_defs = ", ".join(f"{name} VARCHAR" for name in COLUMNS)
    csv_columns = ", ".join(f"'{name}': 'VARCHAR'" for name in COLUMNS)
    source_file = path.name

    with duckdb.connect(str(db_path)) as connection:
        connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS raw.price_paid (
                {column_defs},
                source_file VARCHAR NOT NULL,
                loaded_at TIMESTAMP NOT NULL
            )
            """
        )
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                "DELETE FROM raw.price_paid WHERE source_file = ?", [source_file]
            )
            connection.execute(
                f"""
                INSERT INTO raw.price_paid
                SELECT *, ? AS source_file, current_timestamp::TIMESTAMP AS loaded_at
                FROM read_csv(
                    ?,
                    header = false,
                    auto_detect = false,
                    delim = ',',
                    quote = '"',
                    escape = '"',
                    columns = {{{csv_columns}}}
                )
                """,
                [source_file, str(path)],
            )
            loaded = connection.execute(
                "SELECT count(*) FROM raw.price_paid WHERE source_file = ?",
                [source_file],
            ).fetchone()[0]
            if loaded != expected_rows:
                raise IngestError(
                    f"loaded {loaded:,} rows but the file has {expected_rows:,}"
                )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return loaded


def run(year: int, db_path: Path = DEFAULT_DB, force: bool = False) -> None:
    destination = RAW_DIR / f"pp-{year}.csv"
    downloaded = download_file(file_url(year), destination, force=force)
    print(f"{'Downloaded' if downloaded else 'Using existing'} {destination}")

    result = validate_csv(destination, year)
    print(
        f"Validated {result.rows:,} rows: {result.bad_rows:,} bad, "
        f"{result.outside_year:,} dated outside {year}"
    )

    loaded = load_csv(destination, db_path, result.rows)
    print(f"Loaded {loaded:,} rows into raw.price_paid in {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--force", action="store_true", help="download again")
    args = parser.parse_args()
    run(args.year, args.db, args.force)


if __name__ == "__main__":
    main()
