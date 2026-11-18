import csv
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pipeline.ingest import COLUMNS, IngestError, download_file, load_csv, validate_csv


def sale(number=1, price="250000", when="2025-03-14 00:00", street="HIGH STREET, EAST"):
    return [
        f"{{ID-{number}}}", price, when, "E1 6AN", "F", "N", "L", "10", "", street,
        "", "LONDON", "TOWER HAMLETS", "GREATER LONDON", "A", "A",
    ]


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        csv.writer(output, quoting=csv.QUOTE_ALL).writerows(rows)
    return path


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")

    class Handler(BaseHTTPRequestHandler):
        responses = []
        requests_seen = 0

        def do_GET(self):
            type(self).requests_seen += 1
            status, body, claimed_length = type(self).responses.pop(0)
            self.send_response(status)
            self.send_header("Content-Length", str(claimed_length or len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield Handler, f"http://127.0.0.1:{httpd.server_port}/pp.csv"
    httpd.shutdown()
    httpd.server_close()


def test_download_writes_complete_file(server, tmp_path):
    handler, url = server
    handler.responses = [(200, b"data", None)]
    destination = tmp_path / "raw" / "pp.csv"

    assert download_file(url, destination, backoff_seconds=0) is True
    assert destination.read_bytes() == b"data"
    assert not (tmp_path / "raw" / "pp.csv.part").exists()


def test_existing_file_is_not_downloaded_again(server, tmp_path):
    handler, url = server
    destination = tmp_path / "pp.csv"
    destination.write_text("existing")

    assert download_file(url, destination) is False
    assert handler.requests_seen == 0


def test_server_error_is_retried(server, tmp_path):
    handler, url = server
    handler.responses = [(503, b"busy", None), (200, b"data", None)]
    destination = tmp_path / "pp.csv"

    assert download_file(url, destination, backoff_seconds=0) is True
    assert destination.read_bytes() == b"data"
    assert handler.requests_seen == 2


def test_missing_file_fails_without_retrying(server, tmp_path):
    handler, url = server
    handler.responses = [(404, b"missing", None)]

    with pytest.raises(IngestError, match="404"):
        download_file(url, tmp_path / "pp.csv", backoff_seconds=0)
    assert handler.requests_seen == 1


def test_failed_download_keeps_previous_file(server, tmp_path):
    handler, url = server
    handler.responses = [(503, b"", None)]
    destination = tmp_path / "pp.csv"
    destination.write_text("good copy")

    with pytest.raises(IngestError):
        download_file(url, destination, force=True, attempts=1)
    assert destination.read_text() == "good copy"
    assert not (tmp_path / "pp.csv.part").exists()


def test_validation_counts_rows(tmp_path):
    path = write_rows(
        tmp_path / "pp.csv",
        [sale(1), sale(2, when="2024-12-31 00:00")],
    )
    result = validate_csv(path, 2025)
    assert (result.rows, result.bad_rows, result.outside_year) == (2, 0, 1)


@pytest.mark.parametrize(
    "bad_row",
    [
        sale(price="free"),
        sale(price="0"),
        sale(when="14/03/2025"),
        sale(when="2025-13-40 00:00"),
        sale()[:-1],
        [""] + sale()[1:],
    ],
)
def test_too_many_bad_rows_stop_the_load(tmp_path, bad_row):
    path = write_rows(tmp_path / "pp.csv", [sale(1), bad_row])
    with pytest.raises(IngestError, match="bad rows"):
        validate_csv(path, 2025)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "pp.csv"
    path.write_text("")
    with pytest.raises(IngestError, match="no rows"):
        validate_csv(path, 2025)


def test_load_keeps_text_and_can_be_repeated(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    path = write_rows(tmp_path / "pp-2025.csv", [sale(1), sale(2)])
    database = tmp_path / "warehouse.duckdb"

    assert load_csv(path, database, 2) == 2
    assert load_csv(path, database, 2) == 2

    with duckdb.connect(str(database)) as connection:
        rows = connection.execute(
            "SELECT transaction_id, price, street, source_file "
            "FROM raw.price_paid ORDER BY transaction_id"
        ).fetchall()
        names = [row[1] for row in connection.execute(
            "SELECT ordinal_position, column_name FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'price_paid' "
            "ORDER BY ordinal_position"
        ).fetchall()]

    assert rows[0] == ("{ID-1}", "250000", "HIGH STREET, EAST", "pp-2025.csv")
    assert len(rows) == 2
    assert names[: len(COLUMNS)] == COLUMNS


def test_row_count_mismatch_leaves_existing_data(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    path = write_rows(tmp_path / "pp-2025.csv", [sale(1)])
    database = tmp_path / "warehouse.duckdb"
    load_csv(path, database, 1)

    write_rows(path, [sale(2), sale(3)])
    with pytest.raises(IngestError, match="loaded 2"):
        load_csv(path, database, 5)

    with duckdb.connect(str(database)) as connection:
        rows = connection.execute("SELECT transaction_id FROM raw.price_paid").fetchall()
    assert rows == [("{ID-1}",)]
