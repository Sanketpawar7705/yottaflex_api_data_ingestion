"""End-to-end tests: a real mock API (uvicorn thread) + the real pipeline + a temporary SQLite file."""
import json
import threading
import time
from dataclasses import replace

import pytest
import requests
import uvicorn

from app.client import APIClient, AuthError, RetryExhausted
from app.config import Settings
from app.mock_api import app, expected_labels
from app.pipeline import run
from app.report import reconcile
from app.storage import connect

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def server():
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            requests.get(URL + "/health", timeout=0.2)
            break
        except requests.RequestException:
            time.sleep(0.1)
    yield URL
    srv.should_exit = True
    thread.join(3)


class Api:
    def post(self, path, body=None):
        requests.post(URL + path, json=body, timeout=5).raise_for_status()

    def load(self, records):
        self.post("/admin/load", {"records": records})

    def append(self, records):
        self.post("/admin/append", {"records": records})

    def faults(self, **kwargs):
        self.post("/admin/configure", kwargs)


@pytest.fixture
def api(server):
    helper = Api()
    helper.post("/admin/reset")
    yield helper
    helper.post("/admin/reset")


@pytest.fixture
def settings(server):
    return replace(Settings(), api_base_url=server, page_size=50, backoff_base=0.001, max_retries=5)


def ev(i=1, **changes):
    record = {"event_id": f"EVT-{i:07d}", "customer_id": "CUST-0001", "amount": 10.0, "currency": "INR",
              "status": "pending", "event_time": "2026-03-01T09:00:00Z", "updated_at": "2026-03-01T10:00:00Z"}
    record.update(changes)
    return record


def go(tmp_path, settings, **kwargs):
    return run(str(tmp_path / "t.db"), settings=settings, **kwargs)


def query(tmp_path, sql, *args):
    conn = connect(str(tmp_path / "t.db"))
    rows = [tuple(r) for r in conn.execute(sql, args)]
    conn.close()
    return rows


def one(tmp_path, sql, *args):
    return query(tmp_path, sql, *args)[0][0]


# ---------------------------------------------------------------------------- API client
def test_client_does_not_retry_auth_errors(server):
    sleeps = []
    client = APIClient(server, "wrong-key", sleep=sleeps.append)
    with pytest.raises(AuthError):
        client.get("/records", {"page": 1, "page_size": 10})
    assert sleeps == []


def test_client_backs_off_exponentially_then_gives_up(server, api):
    api.faults(fail_every=1)                                     # every request -> 503
    sleeps = []
    client = APIClient(server, "local-demo-token", max_retries=3, backoff_base=0.1, sleep=sleeps.append)
    with pytest.raises(RetryExhausted):
        client.get("/records", {"page": 1, "page_size": 10})
    assert client.retries == 3 and sleeps[0] < sleeps[1] < sleeps[2]


# ---------------------------------------------------------------------------- happy path
def test_full_load_matches_expected_labels(api, settings, tmp_path):
    result = go(tmp_path, settings)
    assert result["status"] == "success"
    conn = connect(str(tmp_path / "t.db"))
    report = reconcile(conn, expected_labels(250))
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    assert result["rejected"] > 0 and result["duplicates"] > 0 and result["late_ignored"] > 0
    assert result["received"] == (result["inserted"] + result["updated"] + result["duplicates"]
                                  + result["late_ignored"] + result["rejected"])


def test_empty_batch(api, settings, tmp_path):
    api.load([])
    result = go(tmp_path, settings)
    assert result["status"] == "success" and result["received"] == 0
    assert one(tmp_path, "SELECT COUNT(*) FROM raw_responses") == 3          # 2 customer pages + 1 empty page
    assert one(tmp_path, "SELECT COUNT(*) FROM checkpoints") == 0


# ---------------------------------------------------------------------------- bad data
def test_malformed_null_and_missing_records_are_quarantined(api, settings, tmp_path):
    missing_currency = ev(5)
    del missing_currency["currency"]
    api.load([ev(1), "garbage", None, 123, ev(2, amount=None), missing_currency, ev(3, customer_id="CUST-9999")])
    result = go(tmp_path, settings)
    assert result["inserted"] == 1 and result["rejected"] == 6
    reasons = {r[0] for r in query(tmp_path, "SELECT reason FROM rejects")}
    assert reasons == {"malformed_record", "invalid_amount:not_numeric", "missing_field:currency",
                       "invalid_customer_ref"}
    source_file, raw = query(tmp_path, "SELECT source_file, raw_record FROM rejects WHERE reason='invalid_customer_ref'")[0]
    assert "EVT-0000003" in raw
    assert one(tmp_path, "SELECT COUNT(*) FROM raw_responses WHERE source_file=?", source_file) == 1


def test_boundary_amounts_load_and_future_timestamp_cannot_poison_checkpoint(api, settings, tmp_path):
    api.load([ev(1, amount=0), ev(2, amount=0.01), ev(3, amount=99999.99), ev(4, amount=1.234),
              ev(5, updated_at="2099-01-01T00:00:00Z")])
    result = go(tmp_path, settings)
    assert [r[0] for r in query(tmp_path, "SELECT amount_minor FROM events ORDER BY event_id")] == [0, 1, 9999999]
    assert result["rejected"] == 2
    assert one(tmp_path, "SELECT last_updated_at FROM checkpoints") == "2026-03-01T10:00:00Z"


# ---------------------------------------------------------------------------- duplicates and versions
def test_exact_duplicates_are_loaded_once(api, settings, tmp_path):
    api.load([ev(1), ev(1), ev(1)])
    result = go(tmp_path, settings)
    assert result["inserted"] == 1 and result["duplicates"] == 2
    assert one(tmp_path, "SELECT COUNT(*) FROM events") == 1


def test_newer_version_in_the_same_run_wins(api, settings, tmp_path):
    # regression: the first version of this project dropped the second record as a "duplicate"
    api.load([ev(1, status="pending", updated_at="2026-03-01T10:00:00Z"),
              ev(1, status="completed", amount=9.0, updated_at="2026-03-01T10:05:00Z")])
    result = go(tmp_path, settings)
    assert result["inserted"] == 1 and result["updated"] == 1
    assert query(tmp_path, "SELECT status, amount_minor FROM events") == [("completed", 900)]
    assert one(tmp_path, "SELECT COUNT(*) FROM events_history") == 2


def test_out_of_order_older_version_is_kept_only_in_history(api, settings, tmp_path):
    api.load([ev(1, status="completed", updated_at="2026-03-01T12:00:00Z"),
              ev(1, status="pending", updated_at="2026-03-01T10:00:00Z")])
    result = go(tmp_path, settings)
    assert result["late_ignored"] == 1
    assert one(tmp_path, "SELECT status FROM events") == "completed"
    assert one(tmp_path, "SELECT COUNT(*) FROM events_history") == 2


# ---------------------------------------------------------------------------- reruns, checkpoints, backfill
def test_rerun_of_same_input_changes_nothing(api, settings, tmp_path):
    go(tmp_path, settings)
    tables = ("events", "events_history", "customers")
    before = {t: query(tmp_path, f"SELECT * FROM {t} ORDER BY 1,2") for t in tables}
    rejects_before = query(tmp_path, "SELECT reject_key, reason FROM rejects ORDER BY 1")
    second = go(tmp_path, settings)
    assert second["status"] == "success" and second["inserted"] == 0 and second["updated"] == 0
    for table in tables:
        assert before[table] == query(tmp_path, f"SELECT * FROM {table} ORDER BY 1,2")
    assert rejects_before == query(tmp_path, "SELECT reject_key, reason FROM rejects ORDER BY 1")
    assert one(tmp_path, "SELECT MAX(seen_count) FROM rejects") >= 2          # re-seen, not duplicated


def test_incremental_run_late_arrival_and_backfill(api, settings, tmp_path):
    api.load([ev(1, updated_at="2026-03-01T10:00:00Z")])
    assert go(tmp_path, settings)["inserted"] == 1
    api.append([ev(2, updated_at="2026-03-02T10:00:00Z")])
    second = go(tmp_path, settings)             # reads since (checkpoint - 1h): event 1 again + new event 2
    assert second["received"] == 2 and second["inserted"] == 1 and second["duplicates"] == 1
    api.append([ev(3, updated_at="2026-03-02T09:30:00Z")])          # late, but inside the lookback window
    assert go(tmp_path, settings)["inserted"] == 1
    api.append([ev(4, updated_at="2026-02-01T00:00:00Z")])          # later than the lookback: missed ...
    go(tmp_path, settings)
    assert one(tmp_path, "SELECT COUNT(*) FROM events") == 3
    backfill = go(tmp_path, settings, since="2026-01-01T00:00:00Z")      # ... recovered by an explicit backfill
    assert backfill["inserted"] == 1 and one(tmp_path, "SELECT COUNT(*) FROM events") == 4


# ---------------------------------------------------------------------------- transient failures and recovery
def test_rate_limit_and_transient_error_are_retried(api, settings, tmp_path):
    api.faults(rate_limit_every=2, fail_once=True)
    result = go(tmp_path, settings)
    assert result["status"] == "success" and result["retries"] > 0 and result["rate_limited"] > 0
    assert reconcile(connect(str(tmp_path / "t.db")), expected_labels(250))["passed"]


def test_truncated_json_page_is_retried(api, settings, tmp_path):
    api.faults(corrupt_every=3)
    result = go(tmp_path, settings)
    assert result["status"] == "success" and result["retries"] > 0
    assert reconcile(connect(str(tmp_path / "t.db")), expected_labels(250))["passed"]


def test_partial_failure_then_restart(api, settings, tmp_path):
    api.faults(fail_every=3)
    first = go(tmp_path, replace(settings, max_retries=0))
    assert first["status"] == "failed" and "RetryExhausted" in first["error"]
    assert one(tmp_path, "SELECT COUNT(*) FROM checkpoints") == 0          # checkpoint did not move
    assert one(tmp_path, "SELECT status FROM runs WHERE run_id=?", first["run_id"]) == "failed"
    api.faults()                                                              # the source recovers
    second = go(tmp_path, settings)
    assert second["status"] == "success"
    assert reconcile(connect(str(tmp_path / "t.db")), expected_labels(250))["passed"]


def test_wrong_api_key_fails_the_run_cleanly(api, settings, tmp_path):
    result = go(tmp_path, replace(settings, api_token="wrong"))
    assert result["status"] == "failed" and "AuthError" in result["error"]
    assert one(tmp_path, "SELECT COUNT(*) FROM events") == 0


# ---------------------------------------------------------------------------- schema changes
def test_additive_new_field_is_tolerated_and_counted(api, settings, tmp_path):
    api.load([ev(1), ev(2)])
    api.faults(schema_drift=True)                   # adds a vendor field to the first record of each page
    result = go(tmp_path, settings)
    assert result["status"] == "success" and result["inserted"] == 2 and result["unexpected_field_records"] == 1


def test_breaking_schema_change_stops_the_run_and_keeps_raw(api, settings, tmp_path):
    api.faults(rename_amount=True)                  # `amount` is now `total_amount`
    result = go(tmp_path, settings)
    assert result["status"] == "failed" and "SchemaDriftError" in result["error"]
    assert one(tmp_path, "SELECT COUNT(*) FROM events") == 0
    assert one(tmp_path, "SELECT COUNT(*) FROM checkpoints") == 0
    assert one(tmp_path, "SELECT COUNT(*) FROM raw_responses WHERE endpoint='records'") >= 1
    api.faults()                                    # upstream fixed -> restart works
    assert go(tmp_path, settings)["status"] == "success"
    assert reconcile(connect(str(tmp_path / "t.db")), expected_labels(250))["passed"]


# ---------------------------------------------------------------------------- observability
def test_raw_pages_and_run_metrics_are_recorded(api, settings, tmp_path):
    result = go(tmp_path, settings)
    conn = connect(str(tmp_path / "t.db"))
    for row in conn.execute("SELECT * FROM raw_responses WHERE endpoint='records'"):
        assert len(json.loads(row["body"])["records"]) == row["record_count"]
    run_row = conn.execute("SELECT * FROM runs WHERE run_id=?", (result["run_id"],)).fetchone()
    assert run_row["status"] == "success" and run_row["started_at"] and run_row["ended_at"]
    assert run_row["received"] == result["received"] and run_row["pages"] == 6
    assert run_row["duration_seconds"] is not None
