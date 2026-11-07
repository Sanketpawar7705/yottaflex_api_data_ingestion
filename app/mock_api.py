"""Local deterministic paginated API with authentication and fault injection.

Run:     python -m app.mock_api            (or: uvicorn app.mock_api:app)
Labels:  python -m app.mock_api labels --count 250 --out data/expected_labels.json
Docs:    http://127.0.0.1:8000/docs   (use the header X-API-Key: local-demo-token)
"""
import argparse
import copy
import json
import math
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel

TOKEN = os.getenv("API_TOKEN", "local-demo-token")
COUNT = int(os.getenv("MOCK_RECORD_COUNT", "250"))
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
CUSTOMERS = [{"customer_id": f"CUST-{i:04d}", "name": f"Customer {i}", "country": ("IN", "US", "DE", "GB")[i % 4]}
             for i in range(1, 101)]


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_records(count):
    """Deterministic source data in ARRIVAL order. Returns (records, defect_labels).

    defect_labels[i] is None for a valid record, otherwise the reject category the pipeline must report.
    The labels are NOT part of the records; they are only used to build expected_labels().
    """
    records, labels = [], []
    for i in range(count):
        t = BASE_TIME + timedelta(minutes=i)
        record = {
            "event_id": f"EVT-{i + 1:07d}",
            "customer_id": f"CUST-{i % 100 + 1:04d}",
            "amount": round((i % 50000 + 1) / 100, 2),
            "currency": "INR" if i % 3 else "USD",
            "status": ("pending", "completed", "cancelled")[i % 3],
            "event_time": iso(t - timedelta(minutes=i % 7)),
            "updated_at": iso(t),
        }
        found = []                                              # same order as validate_event()
        if i and i % 71 == 0:
            del record["currency"]; found.append("missing_field")
        if i and i % 97 == 0:
            record["customer_id"] = "CUST-INVALID"; found.append("invalid_customer_ref")
        if i and i % 79 == 0:
            record["amount"] = None; found.append("invalid_amount")
        if i and i % 89 == 0:
            record["amount"] = -1; found.append("invalid_amount")
        if i and i % 73 == 0:
            record["event_time"] = "not-a-date"; found.append("invalid_timestamp")
        if i and i % 67 == 0:
            record["updated_at"] = "2099-01-01T00:00:00Z"; found.append("future_timestamp")
        if i and i % 83 == 0:                                   # second version of the previous event
            record["event_id"] = f"EVT-{i:07d}"
            if (i // 83) % 2 == 1:
                record["updated_at"] = iso(t - timedelta(minutes=2))      # OLDER version arriving late
        defect = found[0] if found else None
        records.append(record)
        labels.append(defect)
        if i and i % 61 == 0 and defect is None:                # exact duplicate delivery
            records.append(copy.deepcopy(record))
            labels.append(None)
    return records, labels


def expected_labels(count):
    """Expected answers, computed from the generator's own defect labels (independent of the pipeline)."""
    records, defects = generate_records(count)
    seen, current = set(), {}
    inserted = updated = duplicates = late = 0
    rejects = {}
    for record, defect in zip(records, defects):
        if defect:
            rejects[defect] = rejects.get(defect, 0) + 1
            continue
        key = (record["event_id"], record["updated_at"])
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        existing = current.get(record["event_id"])
        if existing is None:
            inserted += 1
            current[record["event_id"]] = record
        elif record["updated_at"] > existing["updated_at"]:
            updated += 1
            current[record["event_id"]] = record
        else:
            late += 1
    return {
        "customers": len(CUSTOMERS),
        "received": len(records), "expected_distinct_valid": len(current),
        "expected_inserted": inserted, "expected_updated": updated,
        "expected_duplicates": duplicates, "expected_late_ignored": late,
        "expected_rejects_by_category": rejects,
        "expected_total_amount_minor": sum(int(Decimal(str(r["amount"])) * 100) for r in current.values()),
    }


app = FastAPI(title="YottaFlex Mock Source API")
state = {"records": generate_records(COUNT)[0], "requests": 0, "failed_once": False}
faults = {"rate_limit_every": 0, "fail_once": False, "schema_drift": False, "rename_amount": False,
          "fail_every": 0, "corrupt_every": 0}


def check_key(key):
    if key != TOKEN:
        raise HTTPException(401, "Invalid API key")


def maybe_inject_fault():
    """Returns a truncated-body flag, or raises an HTTPException for 429/503."""
    state["requests"] += 1
    n = state["requests"]
    if faults["rate_limit_every"] and n % faults["rate_limit_every"] == 0:
        raise HTTPException(429, "Rate limit injected", headers={"Retry-After": "0"})
    if faults["fail_once"] and not state["failed_once"]:
        state["failed_once"] = True
        raise HTTPException(503, "One-time transient failure")
    if faults["fail_every"] and n % faults["fail_every"] == 0:
        raise HTTPException(503, "Periodic transient failure")
    return bool(faults["corrupt_every"] and n % faults["corrupt_every"] == 0)


def paginate(rows, page, page_size):
    start = (page - 1) * page_size
    return {"page": page, "page_size": page_size, "total": len(rows),
            "total_pages": math.ceil(len(rows) / page_size), "records": [dict(r) if isinstance(r, dict) else r
                                                                          for r in rows[start:start + page_size]]}


def respond(body, corrupt):
    text = json.dumps(body)
    return Response(content=text[: len(text) // 2] if corrupt else text, media_type="application/json")


def newer_than(record, cutoff):
    """Malformed or unparseable records are always served, so the pipeline can quarantine them."""
    try:
        moment = datetime.fromisoformat(record["updated_at"].replace("Z", "+00:00"))
        return moment > cutoff
    except (KeyError, TypeError, ValueError, AttributeError):
        return True


@app.get("/health")
def health():
    return {"status": "ok", "records": len(state["records"])}


@app.get("/customers")
def get_customers(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=5000),
                  x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    corrupt = maybe_inject_fault()
    return respond(paginate(CUSTOMERS, page, page_size), corrupt)


@app.get("/records")
def get_records(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=5000),
                updated_after: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    corrupt = maybe_inject_fault()
    rows = state["records"]
    if updated_after:
        try:
            cutoff = datetime.fromisoformat(updated_after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "updated_after must be ISO-8601")
        rows = [r for r in rows if newer_than(r, cutoff)]
    body = paginate(rows, page, page_size)
    chunk = body["records"]
    if faults["schema_drift"] and chunk and isinstance(chunk[0], dict):
        chunk[0]["unexpected_vendor_field"] = "drift"                       # additive change
    if faults["rename_amount"]:                                             # breaking change
        body["records"] = [{("total_amount" if k == "amount" else k): v for k, v in r.items()}
                           if isinstance(r, dict) else r for r in chunk]
    return respond(body, corrupt)


class Faults(BaseModel):
    rate_limit_every: int = 0
    fail_once: bool = False
    schema_drift: bool = False
    rename_amount: bool = False
    fail_every: int = 0
    corrupt_every: int = 0


class Load(BaseModel):
    records: List[Any]


@app.post("/admin/configure")
def configure(config: Faults):
    faults.update(config.model_dump())
    state["requests"] = 0
    state["failed_once"] = False
    return {"configured": True}


@app.post("/admin/reset")
def reset():
    state["records"] = generate_records(COUNT)[0]
    state["requests"] = 0
    state["failed_once"] = False
    faults.update({k: (0 if isinstance(v, int) and not isinstance(v, bool) else False) for k, v in faults.items()})
    return {"reset": True, "records": len(state["records"])}


@app.post("/admin/load")
def load(payload: Load):
    """Replace the served records (used by tests to create exact scenarios)."""
    state["records"] = list(payload.records)
    return {"loaded": len(state["records"])}


@app.post("/admin/append")
def append(payload: Load):
    state["records"].extend(payload.records)
    return {"records": len(state["records"])}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m app.mock_api")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    labels = sub.add_parser("labels")
    labels.add_argument("--count", type=int, default=COUNT)
    labels.add_argument("--out", default="data/expected_labels.json")
    args = parser.parse_args(argv)
    if args.cmd == "labels":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(expected_labels(args.count), indent=2))
        print(f"wrote {args.out}")
        return 0
    import uvicorn
    uvicorn.run(app, host=getattr(args, "host", "127.0.0.1"), port=getattr(args, "port", 8000))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
