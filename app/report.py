"""Reconciliation report: proves the target is consistent and explains the differences.

Usage:  python -m app.report [--db data/ingestion.db] [--labels data/expected_labels.json]
Exit code 0 = every check passed, 1 = at least one failed.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from app.storage import connect

CATEGORY = "substr(reason, 1, instr(reason || ':', ':') - 1)"


def reconcile(conn, labels=None):
    checks = []

    def add(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    def scalar(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    unbalanced = [dict(r) for r in conn.execute(
        "SELECT run_id, received, inserted, updated, duplicates, late_ignored, rejected FROM runs "
        "WHERE status='success' AND received != inserted+updated+duplicates+late_ignored+rejected")]
    add("every successful run: received = inserted + updated + duplicates + late_ignored + rejected",
        not unbalanced, unbalanced or "all runs balance")
    orphans = scalar("SELECT COUNT(*) FROM events e LEFT JOIN customers c USING(customer_id) "
                     "WHERE c.customer_id IS NULL")
    add("referential integrity: every event has a customer", orphans == 0, f"orphans={orphans}")
    events, history_events = scalar("SELECT COUNT(*) FROM events"), scalar("SELECT COUNT(DISTINCT event_id) FROM events_history")
    add("events holds exactly one row per event in history", events == history_events,
        f"events={events} history_distinct={history_events}")
    stale = scalar("""SELECT COUNT(*) FROM events e JOIN
                      (SELECT event_id, MAX(updated_at) m FROM events_history GROUP BY event_id) h USING(event_id)
                      WHERE e.updated_at != h.m""")
    add("events always holds the newest version", stale == 0, f"stale={stale}")
    untraceable = scalar("SELECT COUNT(*) FROM rejects r LEFT JOIN raw_responses f USING(source_file) "
                         "WHERE f.source_file IS NULL")
    add("every reject is traceable to a retained raw response", untraceable == 0, f"untraceable={untraceable}")
    damaged = [r["source_file"] for r in conn.execute("SELECT source_file, sha256, body FROM raw_responses")
               if hashlib.sha256(r["body"].encode("utf-8")).hexdigest() != r["sha256"]]
    add("raw responses match their SHA-256", not damaged, damaged[:5] or "ok")

    if labels:
        total = scalar("SELECT COALESCE(SUM(amount_minor),0) FROM events")
        add("labels: distinct valid events", events == labels["expected_distinct_valid"],
            f"actual={events} expected={labels['expected_distinct_valid']}")
        add("labels: SUM(amount_minor)", total == labels["expected_total_amount_minor"],
            f"actual={total} expected={labels['expected_total_amount_minor']}")
        actual = {r[0]: r[1] for r in conn.execute(f"SELECT {CATEGORY}, COUNT(*) FROM rejects GROUP BY 1")}
        add("labels: rejects by category", actual == labels["expected_rejects_by_category"],
            f"actual={actual} expected={labels['expected_rejects_by_category']}")
        first = conn.execute("SELECT * FROM runs ORDER BY started_at LIMIT 1").fetchone()
        if first is not None and first["status"] == "success" and first["since"] is None:
            pairs = [("received", "received"), ("inserted", "expected_inserted"), ("updated", "expected_updated"),
                     ("duplicates", "expected_duplicates"), ("late_ignored", "expected_late_ignored")]
            diffs = {a: (first[a], labels[b]) for a, b in pairs if first[a] != labels[b]}
            add("labels: counters of the first full run", not diffs, diffs or "match")
        else:
            add("labels: counters of the first full run", True,
                "skipped: the first run was not a clean full load (re-read pages are legitimately duplicates)")
    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def to_markdown(report):
    lines = ["# Reconciliation report", "", f"**Overall: {'PASS' if report['passed'] else 'FAIL'}**", "",
             "| Result | Check | Detail |", "|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {'PASS' if c['passed'] else 'FAIL'} | {c['check']} | {str(c['detail'])[:150]} |")
    return "\n".join(lines) + "\n"


def run_history(conn, limit=10):
    return [dict(r) for r in conn.execute(
        "SELECT run_id, status, started_at, received, inserted, updated, duplicates, late_ignored, rejected, "
        "retries, rate_limited, error FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reconcile the target tables")
    parser.add_argument("--db", default="data/ingestion.db")
    parser.add_argument("--labels", help="expected-answer labels (python -m app.mock_api labels)")
    parser.add_argument("--report-dir", default="reports")
    args = parser.parse_args(argv)
    labels = json.loads(Path(args.labels).read_text()) if args.labels else None
    conn = connect(args.db)
    report = reconcile(conn, labels)
    history = run_history(conn)
    conn.close()
    out = Path(args.report_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconciliation_report.json").write_text(json.dumps({**report, "runs": history}, indent=2))
    (out / "reconciliation_report.md").write_text(to_markdown(report))
    print(to_markdown(report))
    print(json.dumps(history[:3], indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
