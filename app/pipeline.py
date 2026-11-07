"""Incremental ingestion: fetch pages -> keep raw -> validate -> load -> checkpoint.

Recovery model
  * every page is loaded in ONE transaction (all or nothing);
  * the checkpoint moves only after the whole run succeeded, so a failed run is simply re-run;
  * loads are idempotent (see storage.load_event), so re-reading pages never creates duplicates.

Usage:  python -m app.pipeline [--since 2026-01-01T00:00:00Z] [--db path]
"""
import argparse
import json
import logging
import sys
import time
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone

from app.client import APIClient
from app.config import Settings
from app.storage import (connect, get_checkpoint, load_event, save_reject, set_checkpoint, store_raw)
from app.validation import RejectError, future_limit_for, parse_timestamp, validate_event

log = logging.getLogger("pipeline")
SOURCE = "mock_api"
DRIFT_MIN_RECORDS = 5       # a page needs at least this many records before we judge it
DRIFT_THRESHOLD = 0.5       # this share of records missing required fields => upstream schema changed


class SchemaError(Exception):
    """The response does not have the shape we expect."""


class SchemaDriftError(SchemaError):
    """A required field disappeared from most records (e.g. it was renamed upstream)."""


@dataclass
class Counters:
    pages: int = 0
    received: int = 0
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    late_ignored: int = 0
    rejected: int = 0
    unexpected_field_records: int = 0
    missing_field_rejects: int = 0

    def add(self, other):
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))


class SqlCustomerLookup:
    """Baseline lookup: one SELECT per record (used only by the benchmark)."""

    def __init__(self, conn):
        self.conn = conn

    def __contains__(self, customer_id):
        if not isinstance(customer_id, str):
            return False
        return self.conn.execute("SELECT 1 FROM customers WHERE customer_id=?", (customer_id,)).fetchone() is not None


def utc_now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_envelope(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise SchemaError("unexpected API response shape (expected an object with a 'records' list)")
    total_pages = payload.get("total_pages")
    return payload["records"], total_pages if isinstance(total_pages, int) else 1


def fetch_pages(conn, client, run_id, endpoint, page_size, extra_params=None):
    """Yield (page_number, source_file, records). Raw text is stored before it is parsed."""
    page = 1
    while True:
        params = {"page": page, "page_size": page_size, **(extra_params or {})}
        status, body, payload = client.get(f"/{endpoint}", params)
        source_file = store_raw(conn, run_id, endpoint, page, status, body, iso(utc_now()))
        records, total_pages = read_envelope(payload)
        yield page, source_file, records
        if page >= total_pages or not records:
            return
        page += 1


def load_customers(conn, client, run_id, settings):
    """Reference data first: events must point to a customer we know."""
    for _page, source_file, records in fetch_pages(conn, client, run_id, "customers", settings.page_size):
        with conn:
            conn.execute("UPDATE raw_responses SET record_count=? WHERE source_file=?", (len(records), source_file))
            for rec in records:
                if isinstance(rec, dict) and isinstance(rec.get("customer_id"), str):
                    conn.execute(                      # rewrite only if something really changed
                        """INSERT INTO customers(customer_id,name,country,run_id,source_file) VALUES(?,?,?,?,?)
                           ON CONFLICT(customer_id) DO UPDATE SET name=excluded.name, country=excluded.country,
                           run_id=excluded.run_id, source_file=excluded.source_file
                           WHERE customers.name IS NOT excluded.name OR customers.country IS NOT excluded.country""",
                        (rec["customer_id"], rec.get("name"), rec.get("country"), run_id, source_file))


def customer_ids_for(conn, settings):
    if settings.customer_lookup == "sql":
        return SqlCustomerLookup(conn)
    return {row[0] for row in conn.execute("SELECT customer_id FROM customers")}


def process_event_page(conn, run_id, source_file, records, customer_ids, now, counters):
    """Validate and load one page. Returns the newest valid updated_at on the page (or None)."""
    newest = None
    now_text = iso(now)
    future_limit = future_limit_for(now)               # computed once per page, not once per record
    for record in records:
        counters.received += 1
        try:
            row, unexpected = validate_event(record, customer_ids, future_limit=future_limit)
        except RejectError as err:
            save_reject(conn, run_id, source_file, record, err.reason, now_text)
            counters.rejected += 1
            if err.reason.startswith("missing_field"):
                counters.missing_field_rejects += 1
            continue
        if unexpected:
            counters.unexpected_field_records += 1      # new extra field: tolerated, but counted
        outcome = load_event(conn, row, run_id, source_file, now_text)
        setattr(counters, outcome, getattr(counters, outcome) + 1)
        if newest is None or row["updated_at"] > newest:
            newest = row["updated_at"]
    return newest


def check_for_schema_drift(page_counters, source_file):
    if (page_counters.received >= DRIFT_MIN_RECORDS
            and page_counters.missing_field_rejects / page_counters.received >= DRIFT_THRESHOLD):
        raise SchemaDriftError(
            f"{page_counters.missing_field_rejects}/{page_counters.received} records in {source_file} "
            "miss required fields - the source schema probably changed; stopping before loading bad data")


def resolve_updated_after(conn, settings, since):
    if since:                                            # explicit backfill: exactly the requested start
        return parse_timestamp(since, "since")
    checkpoint = get_checkpoint(conn, SOURCE)
    if checkpoint:                                       # incremental: step back to catch late arrivals
        moment = datetime.strptime(checkpoint, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return iso(moment - timedelta(seconds=settings.lookback_seconds))
    return None


def run(path=None, since=None, settings=None, client=None):
    settings = settings or Settings.from_env()
    conn = connect(path or settings.database_path)
    client = client or APIClient(settings.api_base_url, settings.api_token, settings.max_retries,
                                 settings.request_timeout, settings.backoff_base)
    run_id = str(uuid.uuid4())
    started = utc_now()
    clock = time.perf_counter()
    counters = Counters()
    error = None
    updated_after = None
    with conn:
        conn.execute("INSERT INTO runs(run_id,started_at,status) VALUES(?,?,?)", (run_id, iso(started), "running"))
    try:
        load_customers(conn, client, run_id, settings)
        customer_ids = customer_ids_for(conn, settings)
        updated_after = resolve_updated_after(conn, settings, since)
        extra = {"updated_after": updated_after} if updated_after else {}
        log.info("run_id=%s start updated_after=%s", run_id, updated_after)
        newest_overall = None
        for page, source_file, records in fetch_pages(conn, client, run_id, "records", settings.page_size, extra):
            page_counters = Counters(pages=1)
            with conn:                                   # one transaction per page
                conn.execute("UPDATE raw_responses SET record_count=? WHERE source_file=?", (len(records), source_file))
                newest = process_event_page(conn, run_id, source_file, records, customer_ids, started, page_counters)
                check_for_schema_drift(page_counters, source_file)
            counters.add(page_counters)
            if newest and (newest_overall is None or newest > newest_overall):
                newest_overall = newest
            log.info("run_id=%s page=%s rows=%s", run_id, page, len(records))
        with conn:                                       # checkpoint only after every page succeeded
            current = get_checkpoint(conn, SOURCE)
            if newest_overall and (current is None or newest_overall > current):
                set_checkpoint(conn, SOURCE, newest_overall)
    except Exception as exc:                             # recorded in `runs`, shown to the operator
        error = f"{type(exc).__name__}: {exc}"
        log.error("run_id=%s FAILED %s", run_id, error)
    status = "failed" if error else "success"
    duration = round(time.perf_counter() - clock, 3)
    with conn:
        conn.execute(
            """UPDATE runs SET ended_at=?, status=?, since=?, pages=?, received=?, inserted=?, updated=?,
               duplicates=?, late_ignored=?, rejected=?, unexpected_field_records=?, retries=?, rate_limited=?,
               duration_seconds=?, error=? WHERE run_id=?""",
            (iso(utc_now()), status, since, counters.pages, counters.received, counters.inserted, counters.updated,
             counters.duplicates, counters.late_ignored, counters.rejected, counters.unexpected_field_records,
             client.retries, client.rate_limited, duration, error, run_id))
    conn.close()
    result = asdict(counters)
    result.pop("missing_field_rejects")
    result.update(run_id=run_id, status=status, loaded=counters.inserted + counters.updated,
                  retries=client.retries, rate_limited=client.rate_limited, duration_seconds=duration)
    if error:
        result["error"] = error
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the ingestion pipeline")
    parser.add_argument("--since", help="explicit backfill start, ISO-8601 with timezone (default: checkpoint)")
    parser.add_argument("--db", help="database file (default: DATABASE_PATH or data/ingestion.db)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run(args.db, args.since)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
