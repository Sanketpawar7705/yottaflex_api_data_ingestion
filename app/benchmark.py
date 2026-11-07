"""Pipeline throughput benchmark + one optimisation (customer check in memory vs one SELECT per record).

Usage:  python -m app.benchmark --records 100000
The source is served from memory (no HTTP) so the numbers show pipeline + SQLite cost only.
"""
import argparse
import json
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from app.config import Settings
from app.mock_api import CUSTOMERS, generate_records, paginate
from app.pipeline import run


class InMemoryClient:
    """Same interface as APIClient.get(), but answers from memory."""
    retries = 0
    rate_limited = 0

    def __init__(self, records):
        self.records = records

    def get(self, path, params):
        rows = CUSTOMERS if path == "/customers" else self.records
        body = paginate(rows, params["page"], params["page_size"])
        return 200, json.dumps(body), body


def measure(records, lookup, page_size):
    folder = tempfile.mkdtemp(prefix="bench_")
    try:
        settings = replace(Settings(), customer_lookup=lookup, page_size=page_size)
        result = run(f"{folder}/bench.db", settings=settings, client=InMemoryClient(records))
        return {"customer_lookup": lookup, "status": result["status"], "received": result["received"],
                "seconds": result["duration_seconds"],
                "records_per_second": round(result["received"] / result["duration_seconds"])}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=100000)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--out", default="reports/benchmark.json")
    args = parser.parse_args(argv)
    records, _ = generate_records(args.records)
    baseline = measure(records, "sql", args.page_size)
    optimised = measure(records, "memory", args.page_size)
    result = {"source_records": len(records), "page_size": args.page_size, "baseline_sql_lookup": baseline,
              "optimised_memory_lookup": optimised,
              "speedup": round(baseline["seconds"] / optimised["seconds"], 2)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
