# YottaFlex AI — API Data Ingestion (Round 2)

A locally runnable Python pipeline for a paginated REST API: API-key authentication, pagination, retries for
429 / 5xx / network errors / truncated JSON, raw-response retention, validation with a quarantine table,
incremental checkpoints with a lookback window, idempotent loads with change history, run metrics and a
reconciliation report. A FastAPI **mock source API** with fault injection makes every run repeatable.

## Architecture
```text
FastAPI mock API  --(X-API-Key, page/page_size/updated_after)-->  APIClient (retry, backoff, Retry-After)
   /customers, /records                                                |
   faults: 429, 503, truncated JSON, schema drift                      v
                                       per page:  raw_responses (text + sha256, committed first)
                                                  validate each record
                                                     |-- valid   -> events (current) + events_history (versions)
                                                     `-- invalid -> rejects (quarantine, raw record + reason)
                                       end of run: runs (metrics) + checkpoints (watermark)  -> app.report
```

## Setup (Python 3.10+; tested on 3.13)
Run everything from the folder that contains `app/` and `pytest.ini`.
```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
pytest                                   # 39 tests, ~2 s  (output saved in evidence/test_results.txt)
```
If you ran an older version of this project, delete the `data/` folder first (the program tells you if needed).

## Run it (two terminals)
Terminal 1 – source API (keep it running):
```bash
python -m app.mock_api                   # http://127.0.0.1:8000/docs ; key: local-demo-token
```
Terminal 2 – pipeline:
```bash
python -m app.mock_api labels --count 250 --out data/expected_labels.json   # expected answers (separate from input)
python -m app.pipeline                   # 1st run = full load, later runs = incremental (checkpoint - lookback)
python -m app.pipeline                   # rerun of the same input: no new rows
python -m app.pipeline --since 2026-01-01T00:00:00Z      # explicit backfill
python -m app.report --labels data/expected_labels.json  # reconciliation -> reports/ (exit code 1 on failure)
python -m app.benchmark --records 100000
```
Fault injection (while the API runs): `POST /admin/configure` with any of `rate_limit_every`, `fail_once`,
`fail_every`, `corrupt_every`, `schema_drift` (extra field), `rename_amount` (breaking change);
`POST /admin/reset` restores data and faults. Use the Swagger page at `/docs`, or:
```bash
curl -X POST localhost:8000/admin/configure -H "Content-Type: application/json" -d '{"rate_limit_every":2,"fail_once":true}'
```
`MOCK_RECORD_COUNT=100000` (set before starting the API) serves a larger dataset.

## Data model and rules (details: docs/DATA_DICTIONARY.md)
* Source: `customers` (reference) and `records` (events). Grain: one version of one event; key `event_id`, a version is `(event_id, updated_at)`.
* Target: `events` (current row per event), `events_history` (every version), `customers`, `rejects`, `raw_responses`, `runs`, `checkpoints`.
* Rules: all fields required; `customer_id` must exist in `customers`; `amount` numeric, ≥ 0, ≤ 2 decimals (stored as integer `amount_minor`);
  currency `AAA`; status pending/completed/cancelled; timestamps ISO-8601 **with timezone** (stored as UTC `...Z`);
  `updated_at` may not be more than 1 day in the future. Extra unknown fields are **tolerated and counted**
  (`unexpected_field_records`); a required field missing from ≥ 50 % of a page **stops the run**.
* Naming: snake_case, ISO-8601 UTC, `run_id` (uuid) and `source_file` (`<run_id>/<endpoint>/page_NNNN`) on every loaded/rejected row.

## Reliability and idempotency
* Retries (bounded, exponential backoff, `Retry-After` honoured): 429, 500/502/503/504, network errors, truncated JSON. 401/403 and other 4xx fail fast.
* Raw page is stored and committed **before** validation, so it survives even when the page later fails.
* One transaction per page. Checkpoint moves only after all pages succeeded; a failed run is just re-run.
* Loads are idempotent: same version again → `duplicates`; older version arriving later → `late_ignored` (kept in history, current row untouched); newer version → `updated`.
* Rejects are keyed by a hash of reason + content, so reruns do not create duplicate rejects (`seen_count` increases).
* Late arrivals within `LOOKBACK_SECONDS` (1 h) are caught automatically; older ones need `--since` (backfill).

## Tests (`pytest`, 39 passing)
Validation rules and boundaries; client retry/backoff/auth; full load reconciled against expected labels; empty batch;
malformed, null and missing-field records; invalid customer reference; exact duplicates; newer version in the same run wins
(regression test for a bug in the first version); out-of-order versions; rerun changes nothing; incremental + late arrival +
backfill; 429/503 retries; truncated JSON; partial failure and restart; wrong API key; additive and breaking schema change;
raw retention and run metrics.

## Reconciliation (python -m app.report)
Checks that every run balances (`received = inserted + updated + duplicates + late_ignored + rejected`), no orphan events,
`events` = newest version of `events_history`, every reject traces to a stored raw page, raw SHA-256 matches, and — with
`--labels` — distinct valid events, total amount and rejects by category equal the generator's expected answers.
Sample output: `evidence/sample_reconciliation_report.md`, `evidence/sample_queries_output.txt`.

## Performance (python -m app.benchmark, 101,516 source records, page size 1000, source served from memory)
Profiling showed ~46 % of the time in timestamp validation (a future-limit string rebuilt for every record and a
`strftime` call for every timestamp). Optimisation: compute the limit once per page and skip `strftime` for timestamps already
in canonical UTC `...Z` form.

| version | median of 5 runs | records/s |
|---|---|---|
| before | 3.27 s | ~31,000 |
| after | 2.47 s | ~41,000 (≈ 24 % faster) |

Also tried: caching customer ids in memory instead of one SELECT per record (`customer_lookup=memory|sql`) — no measurable gain
(SQLite primary-key lookups are cheap), so it is only kept as a benchmark experiment (`evidence/benchmark.json`).

## Known limitations / next steps
Offset pagination (a real API should offer cursors); single-threaded; SQLite; equal `updated_at` with different content keeps the
first version; data older than the lookback needs `--since`; raw bodies are kept in SQLite (use object storage at scale);
bulk inserts (`executemany`) and parallel page fetching are the next speed-ups.
