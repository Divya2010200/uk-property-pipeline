from types import SimpleNamespace

import pytest

from pipeline.ingest import COLUMNS, IngestError
from pipeline.load_bigquery import LOCATION, load_file, table_id


class FakeBigQuery:
    SourceFormat = SimpleNamespace(CSV="CSV")
    WriteDisposition = SimpleNamespace(WRITE_TRUNCATE="WRITE_TRUNCATE")

    @staticmethod
    def LoadJobConfig(**settings):
        return SimpleNamespace(**settings)

    @staticmethod
    def SchemaField(name, kind):
        return (name, kind)

    @staticmethod
    def Dataset(name):
        return SimpleNamespace(name=name, location=None)


class FakeJob:
    def __init__(self, rows):
        self.output_rows = rows
        self.finished = False

    def result(self):
        self.finished = True


class FakeClient:
    def __init__(self, rows):
        self.job = FakeJob(rows)

    def create_dataset(self, dataset, exists_ok):
        self.dataset = dataset
        self.exists_ok = exists_ok

    def load_table_from_file(self, source, destination, job_config, location):
        self.content = source.read()
        self.destination = destination
        self.config = job_config
        self.location = location
        return self.job


def test_table_name_uses_year():
    assert table_id("my-project", 2025) == "my-project.raw.price_paid_2025"


def test_load_replaces_year_table_with_text_columns(tmp_path):
    path = tmp_path / "pp-2025.csv"
    path.write_bytes(b"data")
    client = FakeClient(rows=2)

    assert load_file(client, FakeBigQuery, path, "p.raw.price_paid_2025", 2) == 2
    assert client.job.finished
    assert client.content == b"data"
    assert client.location == LOCATION
    assert client.dataset.name == "p.raw"
    assert client.dataset.location == LOCATION
    assert client.config.write_disposition == "WRITE_TRUNCATE"
    assert client.config.max_bad_records == 0
    assert client.config.schema == [(name, "STRING") for name in COLUMNS]


def test_row_count_mismatch_fails(tmp_path):
    path = tmp_path / "pp-2025.csv"
    path.write_bytes(b"data")
    with pytest.raises(IngestError, match="loaded 1 rows"):
        load_file(FakeClient(rows=1), FakeBigQuery, path, "p.raw.price_paid_2025", 2)
