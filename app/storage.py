"""SQLite schema, connection and small load helpers."""
import hashlib
import json
import sqlite3
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS runs(
  run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, status TEXT, since TEXT,
  pages INTEGER, received INTEGER, inserted INTEGER, updated INTEGER, duplicates INTEGER,
  late_ignored INTEGER, rejected INTEGER, unexpected_field_records INTEGER,
  retries INTEGER, rate_limited INTEGER, duration_seconds REAL, error TEXT);
CREATE TABLE IF NOT EXISTS raw_responses(
  source_file TEXT PRIMARY KEY, run_id TEXT NOT NULL, endpoint TEXT NOT NULL, page INTEGER NOT NULL,
  fetched_at TEXT NOT NULL, status INTEGER, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
  record_count INTEGER, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers(
  customer_id TEXT PRIMARY KEY, name TEXT, country TEXT, run_id TEXT, source_file TEXT);
CREATE TABLE IF NOT EXISTS events(
  event_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  amount REAL NOT NULL, amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0),
  currency TEXT NOT NULL, status TEXT NOT NULL, event_time TEXT NOT NULL, updated_at TEXT NOT NULL,
  source_file TEXT NOT NULL, run_id TEXT NOT NULL, ingested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events_history(
  event_id TEXT NOT NULL, updated_at TEXT NOT NULL, customer_id TEXT NOT NULL, amount_minor INTEGER NOT NULL,
  currency TEXT NOT NULL, status TEXT NOT NULL, event_time TEXT NOT NULL,
  source_file TEXT NOT NULL, run_id TEXT NOT NULL,
  PRIMARY KEY(event_id, updated_at));
CREATE TABLE IF NOT EXISTS rejects(
  reject_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, source_file TEXT NOT NULL, event_id TEXT,
  reason TEXT NOT NULL, raw_record TEXT NOT NULL, rejected_at TEXT NOT NULL,
  last_run_id TEXT NOT NULL, seen_count INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS checkpoints(source TEXT PRIMARY KEY, last_updated_at TEXT);
CREATE INDEX IF NOT EXISTS idx_events_customer ON events(customer_id);
"""


def connect(path):
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    columns = [row[1] for row in conn.execute("PRAGMA table_info(runs)")]
    if columns and "inserted" not in columns:
        conn.close()
        raise RuntimeError(f"{path} was created by an older version of this project. "
                           "Delete the data/ folder (or set DATABASE_PATH to a new file) and run again.")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(DDL)
    return conn


def store_raw(conn, run_id, endpoint, page, status, body, now):
    """Keep the untouched response text BEFORE parsing it. Committed on its own."""
    source_file = f"{run_id}/{endpoint}/page_{page:04d}"
    encoded = body.encode("utf-8")
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO raw_responses(source_file,run_id,endpoint,page,fetched_at,status,"
            "sha256,bytes,body) VALUES(?,?,?,?,?,?,?,?,?)",
            (source_file, run_id, endpoint, page, now, status, hashlib.sha256(encoded).hexdigest(),
             len(encoded), body))
    return source_file


def save_reject(conn, run_id, source_file, record, reason, now):
    """Quarantine a bad record. The key is a hash of the content, so a rerun cannot duplicate it."""
    raw = json.dumps(record, sort_keys=True, default=str)
    key = hashlib.sha256(f"{reason}|{raw}".encode("utf-8")).hexdigest()
    event_id = record.get("event_id") if isinstance(record, dict) else None
    conn.execute(
        """INSERT INTO rejects(reject_key,run_id,source_file,event_id,reason,raw_record,rejected_at,last_run_id)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(reject_key) DO UPDATE SET last_run_id=excluded.last_run_id, seen_count=seen_count+1""",
        (key, run_id, source_file, event_id if isinstance(event_id, str) else None, reason, raw, now, run_id))


def load_event(conn, row, run_id, source_file, now):
    """Idempotent load. Returns inserted | updated | duplicates | late_ignored."""
    params = dict(row, run_id=run_id, source_file=source_file, ingested_at=now)
    history = conn.execute(
        """INSERT OR IGNORE INTO events_history(event_id,updated_at,customer_id,amount_minor,currency,
           status,event_time,source_file,run_id)
           VALUES(:event_id,:updated_at,:customer_id,:amount_minor,:currency,:status,:event_time,
           :source_file,:run_id)""", params)
    if history.rowcount == 0:                      # this exact version was already stored
        return "duplicates"
    current = conn.execute("SELECT updated_at FROM events WHERE event_id=?", (row["event_id"],)).fetchone()
    if current is not None and row["updated_at"] < current["updated_at"]:
        return "late_ignored"                      # older version arrived later: history keeps it
    conn.execute(
        """INSERT OR REPLACE INTO events(event_id,customer_id,amount,amount_minor,currency,status,event_time,
           updated_at,source_file,run_id,ingested_at)
           VALUES(:event_id,:customer_id,:amount,:amount_minor,:currency,:status,:event_time,:updated_at,
           :source_file,:run_id,:ingested_at)""", params)
    return "inserted" if current is None else "updated"


def get_checkpoint(conn, source):
    row = conn.execute("SELECT last_updated_at FROM checkpoints WHERE source=?", (source,)).fetchone()
    return row["last_updated_at"] if row else None


def set_checkpoint(conn, source, value):
    conn.execute("INSERT INTO checkpoints(source,last_updated_at) VALUES(?,?) "
                 "ON CONFLICT(source) DO UPDATE SET last_updated_at=excluded.last_updated_at", (source, value))
