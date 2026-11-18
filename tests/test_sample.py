from pathlib import Path

from pipeline.ingest import validate_csv


def test_ci_sample_is_valid():
    result = validate_csv(Path("tests/fixtures/price_paid_sample.csv"), 2025)
    assert result.rows == 24
    assert result.bad_rows == 0
    assert result.outside_year == 0
