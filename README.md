# YottaFlex API Data Ingestion Pipeline

A Python-based API data ingestion pipeline demonstrating authenticated API integration, pagination, retry handling, rate-limit management, data validation, raw response retention, incremental checkpoints, idempotent SQLite storage, automated testing, and reconciliation reporting.

**Candidate:** Sanket Pawar  
**Repository:** https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion  
**Language:** Python  
**API framework:** FastAPI  
**Database:** SQLite  
**Testing:** Pytest

---

## 1. Project Overview

This project implements a reliable API data ingestion workflow.

It retrieves customer and event records from an authenticated, paginated API, validates the incoming data, retains the original API responses, and loads valid records into a SQLite database.

The pipeline is designed to handle common data-ingestion problems, including:

- Authenticated API requests.
- Paginated API responses.
- Temporary HTTP errors and rate limits.
- Retry handling with exponential backoff.
- Malformed or invalid records.
- Unexpected fields and schema changes.
- Duplicate event deliveries.
- Older event versions arriving late.
- Incremental ingestion using checkpoints.
- Reconciliation and data-integrity checks.

A local FastAPI mock source is included so the complete workflow can be executed without an external paid API.

## 2. Project Objectives

The main objectives are:

1. Build an executable API ingestion pipeline.
2. Retrieve data using authenticated HTTP requests.
3. Process paginated responses.
4. Handle temporary failures and rate limits.
5. Validate incoming records before loading them.
6. Retain original API response bodies for traceability.
7. Store data consistently in SQLite.
8. Prevent duplicate event versions.
9. Maintain the newest valid version of each event.
10. Support incremental ingestion using checkpoints.
11. Generate reconciliation reports.
12. Verify functionality through automated tests and a benchmark.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main implementation language |
| FastAPI | Local mock API |
| Uvicorn | Runs the mock API server |
| Requests | HTTP API client |
| SQLite | Persistent local storage |
| Pytest | Automated testing |
| Pydantic | API request-model validation |
| Git | Version control |
| GitHub | Public source-code repository |

## 4. Repository Structure

```text
yottaflex_api_data_ingestion/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── client.py
│   ├── mock_api.py
│   ├── pipeline.py
│   ├── validation.py
│   ├── storage.py
│   ├── report.py
│   └── benchmark.py
│
├── tests/
│   └── Automated test files
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   ├── DECISIONS.md
│   └── LIMITATIONS.md
│
├── evidence/
│   ├── test-results/
│   ├── reconciliation/
│   └── benchmark/
│
├── .env.example
├── .gitignore
├── PROMPT_HISTORY.md
├── pytest.ini
├── requirements.txt
└── README.md
```

Runtime directories such as `data/` and `reports/` are generated locally and are excluded from Git.

## 5. Architecture and Data Flow

```text
             Local Mock API
             FastAPI Server
                    |
                    v
             API Client
       Authentication and Pagination
                    |
                    v
          Retry and Rate Limiting
                    |
                    v
          Raw Response Retention
                    |
                    v
            Data Validation
                    |
          +---------+---------+
          |                   |
          v                   v
     Valid Records       Rejected Records
          |                   |
          v                   v
    SQLite Events       SQLite Rejects
          |
          v
    Event History
          |
          v
   Incremental Checkpoint
          |
          v
   Reconciliation Report
```

### Processing workflow

1. The pipeline connects to the configured API.
2. Customer reference data is retrieved first.
3. Event records are fetched page by page.
4. Each original response is stored before parsing.
5. Incoming records are validated.
6. Invalid records are stored in the reject table.
7. Valid events are inserted or updated.
8. Duplicate versions are ignored.
9. Older versions arriving after newer versions are not allowed to replace the current event.
10. A checkpoint is updated after all pages have been processed successfully.
11. Run statistics are recorded.
12. A reconciliation report verifies the resulting data.

## 6. Database Design

The SQLite database contains the following main tables:

| Table | Purpose |
|---|---|
| `runs` | Tracks ingestion runs, status, counters, duration and errors |
| `raw_responses` | Stores original API response bodies and SHA-256 hashes |
| `customers` | Stores customer reference data |
| `events` | Stores the current version of each event |
| `events_history` | Stores distinct event versions |
| `rejects` | Stores rejected records and their reasons |
| `checkpoints` | Stores the latest successful ingestion timestamp |

The `events` table maintains one current record per event ID. The history table retains distinct versions, allowing the pipeline to distinguish new events, updates, duplicates, and late-arriving older versions.

## 7. Requirements

- Windows, Linux, or macOS.
- Python 3.10 or later.
- pip.
- Git.
- Internet access for the initial Python package installation.

The application and mock API run locally after dependencies are installed. No hosted database or paid API is required.

## 8. Installation – Windows PowerShell

Clone the repository:

```powershell
git clone https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion.git
cd yottaflex_api_data_ingestion
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 9. Configuration

The `.env.example` file documents the local configuration:

```env
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=local-demo-token
DATABASE_PATH=data/ingestion.db
PAGE_SIZE=100
MAX_RETRIES=4
LOOKBACK_SECONDS=3600
MOCK_RECORD_COUNT=250
```

For PowerShell, set the variables in the terminal before starting the API and pipeline:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:API_TOKEN = "local-demo-token"
$env:DATABASE_PATH = "data/ingestion.db"
$env:PAGE_SIZE = "100"
$env:MAX_RETRIES = "4"
$env:LOOKBACK_SECONDS = "3600"
$env:MOCK_RECORD_COUNT = "250"
```

These values are for local demonstration only. Do not use demo credentials in production.

## 10. Run the Mock API

Start the local API server:

```powershell
python -m app.mock_api serve --host 127.0.0.1 --port 8000
```

Check the health endpoint:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

The API uses the `X-API-Key` request header.

## 11. Run Automated Tests

Run the complete test suite:

```powershell
python -m pytest -v
```

Run a concise test summary:

```powershell
python -m pytest -q
```

Review the test output and record the actual result in the submission evidence.

## 12. Run the Ingestion Pipeline

Generate expected results for reconciliation:

```powershell
python -m app.mock_api labels --count 250 --out data/expected_labels.json
```

Run the pipeline:

```powershell
python -m app.pipeline
```

The pipeline prints a JSON summary containing run status, pages, received records, inserted records, updated records, duplicates, rejected records, retries, rate limits, and execution duration.

## 13. Generate Reconciliation Reports

Run:

```powershell
python -m app.report --db data/ingestion.db --labels data/expected_labels.json
```

Generated reports:

```text
reports/
    reconciliation_report.json
    reconciliation_report.md
```

The reconciliation process checks:

- Record accounting for successful runs.
- Customer referential integrity.
- Current events against event history.
- Whether the latest event version is stored.
- Whether rejected records can be traced to raw responses.
- Whether stored raw responses match their SHA-256 hashes.
- Expected event totals and reject categories when labels are supplied.

A successful reconciliation exits with code `0`. A failed check exits with code `1`.

## 14. Run the Performance Benchmark

Run the benchmark with 100,000 records:

```powershell
python -m app.benchmark --records 100000 --page-size 1000 --out reports/benchmark.json
```

The benchmark compares:

- Baseline: one SQL customer lookup per record.
- Optimized: customer IDs loaded into memory for validation.

The output includes elapsed time, records per second, and the measured speedup.

This benchmark uses an in-memory source, so it measures pipeline and SQLite lookup costs rather than end-to-end network performance.

## 15. Reliability and Error Handling

The API client retries selected temporary errors:

- HTTP 429 – Too Many Requests.
- HTTP 500 – Internal Server Error.
- HTTP 502 – Bad Gateway.
- HTTP 503 – Service Unavailable.
- HTTP 504 – Gateway Timeout.
- Network request exceptions.
- Malformed JSON responses.

The retry delay uses exponential backoff, with a maximum delay.

Authentication failures such as HTTP 401 and 403 are treated as non-retryable configuration errors.

## 16. Data Quality and Idempotency

The pipeline validates event fields, customer references, amounts, statuses, and timestamps.

Invalid records are retained in the reject table with their raw content and rejection reason.

The storage layer uses event IDs and event timestamps to identify distinct versions. Reprocessing an identical version does not create another event-history entry.

When an older event version arrives after a newer version, the current event is not overwritten by the older data.

## 17. Recovery and Incremental Processing

Each page is loaded in a database transaction.

The checkpoint advances only after the complete ingestion run succeeds. If a run fails, the operator can rerun it.

The pipeline uses a configurable lookback window when reading from a saved checkpoint. This helps catch records that arrive late.

Idempotent loading allows pages to be safely reread without creating duplicate event versions.

## 18. Testing and Validation Evidence

The following checks should be run before submission:

| Validation | Command |
|---|---|
| Automated tests | `python -m pytest -v` |
| API health | `Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"` |
| Ingestion | `python -m app.pipeline` |
| Reconciliation | `python -m app.report --db data/ingestion.db --labels data/expected_labels.json` |
| Benchmark | `python -m app.benchmark --records 100000 --page-size 1000 --out reports/benchmark.json` |

Store genuine screenshots and generated report copies in the `evidence/` directory. Do not include fabricated test output or performance numbers.

## 19. Design Decisions and Trade-offs

- **SQLite:** Chosen because it is lightweight, free, locally runnable, and sufficient for this demonstration.
- **FastAPI mock source:** Provides a reproducible API without depending on an external service.
- **Raw response retention:** Makes it possible to investigate source data and trace rejected records.
- **Per-page transactions:** Avoids partially loading a page.
- **Checkpoint after a successful run:** Avoids advancing the incremental position after a failed ingestion.
- **Idempotent event history:** Allows safe reruns and duplicate detection.
- **In-memory customer lookup:** Reduces repeated SQL queries during validation; the benchmark measures this optimization.

## 20. Limitations and Future Improvements

This is a local demonstration, not a fully deployed production service.

Potential future improvements include:

- Support for a real external API and its authentication scheme.
- More comprehensive configurable retry policies.
- Centralized structured logging and monitoring.
- A production database such as PostgreSQL.
- Scheduling and orchestration.
- Containerized deployment.
- Continuous integration.
- Larger-scale load and failure testing.
- Secure secret management for production environments.

The mock API and its local demo token are intended only for development and testing.

## 21. AI Usage Disclosure

AI tools were used as development assistance during this project.

The prompt history is maintained in `PROMPT_HISTORY.md`.

The candidate should complete that file with the actual prompts sent to each AI tool and explain:

- Where AI accelerated implementation.
- Which implementation areas received substantial AI assistance.
- Which code, tests, design decisions, and documentation were personally reviewed.
- What was run and validated locally.
- Any limitations in the available prompt-history export.

AI-generated suggestions must not be presented as personally verified results unless they were actually reviewed and tested.

## 22. How to Reproduce the Project

1. Clone the public repository.
2. Create and activate a Python virtual environment.
3. Install dependencies.
4. Set the local environment variables.
5. Start the mock API.
6. Check the API health endpoint.
7. Run the automated tests.
8. Generate expected labels.
9. Run the ingestion pipeline.
10. Generate the reconciliation report.
11. Run the benchmark.
12. Inspect the generated database and reports.

## 23. Submission

**GitHub Repository:**  
https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion

The repository includes the Python implementation, tests, supporting documentation, evidence directory, and AI prompt-history disclosure.

---

**Author:** Sanket Pawar  
**Project:** YottaFlex API Data Ingestion Pipeline
