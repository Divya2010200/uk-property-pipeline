"""Load the small synthetic sample used for automated checks."""

import sys
from pathlib import Path

from pipeline.ingest import load_csv, validate_csv

SAMPLE = Path("tests/fixtures/price_paid_sample.csv")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m pipeline.load_sample <database-path>")
    result = validate_csv(SAMPLE, 2025)
    loaded = load_csv(SAMPLE, Path(sys.argv[1]), result.rows)
    print(f"Loaded {loaded} sample rows into {sys.argv[1]}")


if __name__ == "__main__":
    main()
