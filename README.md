# YottaFlex API Data Ingestion Pipeline

<p align="center">
  <strong>A reliable, incremental API data ingestion system built with Python and SQLite.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Local%20Mock%20API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Pytest-Testing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest">
</p>

<p align="center">
  <a href="https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion">GitHub Repository</a>
</p>

---

## 1. Project Overview

This project was developed as part of the **YottaFlex AI Recruitment Drive Candidate Project**.

The objective is to build a practical API data ingestion pipeline that can retrieve data from an API, process it reliably, validate incoming records, and store the results in a local database.

The pipeline is designed around problems that commonly occur in real-world data integrations: paginated responses, temporary API failures, rate limits, duplicate records, invalid data, and events arriving out of order.

A local FastAPI mock API makes it possible to run and validate the complete workflow without depending on a paid external API.

## 2. Key Features

- **API authentication:** sends authenticated requests to the source API.
- **Pagination:** retrieves records across multiple API pages.
- **Retry handling:** retries selected temporary failures.
- **Rate-limit handling:** handles HTTP 429 responses.
- **Exponential backoff:** avoids repeatedly retrying a failing API too quickly.
- **Data validation:** checks incoming records before database loading.
- **Raw response retention:** keeps original API response data for traceability.
- **Incremental ingestion:** uses checkpoints and a configurable lookback window.
- **Idempotent processing:** prevents duplicate event versions from being inserted repeatedly.
- **Late-arriving event handling:** prevents older event versions from replacing newer ones.
- **SQLite storage:** stores customers, events, history, rejects, and ingestion metadata.
- **Reconciliation:** checks whether the stored data is consistent.
- **Automated tests:** verifies pipeline and validation behavior.
- **Benchmarking:** compares database lookup approaches.

## 3. Technology Stack

| Technology | How it is used |
|---|---|
| Python | Application logic and data processing |
| FastAPI | Local mock API |
| Uvicorn | Local API server |
| Requests | HTTP communication |
| SQLite | Local database |
| Pytest | Automated tests |
| Git | Source-code version control |
| GitHub | Public project repository |

## 4. Project Structure

```text
yottaflex_api_data_ingestion/
│
├── app/
│   ├── __init__.py
│   ├── benchmark.py
│   ├── client.py
│   ├── config.py
│   ├── mock_api.py
│   ├── pipeline.py
│   ├── report.py
│   ├── storage.py
│   └── validation.py
│
├── docs/
│   ├── DATA_DICTIONARY.md
│   └── DESIGN_NOTES.md
│
├── evidence/
│   ├── benchmark.json
│   ├── sample_queries_output.txt
│   ├── sample_reconciliation_report.json
│   ├── sample_reconciliation_report.md
│   └── test_results.txt
│
├── tests/
│   ├── test_pipeline.py
│   └── test_validation.py
│
├── .env.example
├── .gitignore
├── PROMPT_HISTORY.md
├── README.md
├── pytest.ini
└── requirements.txt
```

### Main application modules

| File | Responsibility |
|---|---|
| `app/config.py` | Reads application configuration |
| `app/client.py` | Handles API requests, authentication, pagination and retries |
| `app/mock_api.py` | Provides the local mock API and test scenarios |
| `app/pipeline.py` | Coordinates the ingestion workflow |
| `app/validation.py` | Validates incoming customer and event data |
| `app/storage.py` | Manages SQLite storage and database operations |
| `app/report.py` | Generates reconciliation reports |
| `app/benchmark.py` | Runs the performance comparison |

### Supporting files

| File | Purpose |
|---|---|
| `docs/DATA_DICTIONARY.md` | Documents the database and data fields |
| `docs/DESIGN_NOTES.md` | Explains technical decisions and design considerations |
| `evidence/benchmark.json` | Sample benchmark output |
| `evidence/sample_queries_output.txt` | Sample database query output |
| `evidence/sample_reconciliation_report.json` | Sample reconciliation results in JSON |
| `evidence/sample_reconciliation_report.md` | Human-readable reconciliation results |
| `evidence/test_results.txt` | Saved test output |
| `PROMPT_HISTORY.md` | AI-use disclosure and prompt history |
| `.env.example` | Example local configuration |
| `.gitignore` | Files excluded from version control |
| `pytest.ini` | Pytest configuration |
| `requirements.txt` | Python dependencies |

## 5. Architecture

The application follows a simple ingestion workflow:

```text
                DATA SOURCE
                     |
                     v
              LOCAL MOCK API
                  FastAPI
                     |
                     v
                API CLIENT
          Authentication / Pagination
                     |
                     v
             RETRY MECHANISM
          Backoff / Rate-limit Handling
                     |
                     v
            RAW RESPONSE STORAGE
                     |
                     v
              DATA VALIDATION
                     |
              +------+------+
              |             |
              v             v
         VALID DATA     INVALID DATA
              |             |
              v             v
          SQLITE DB      REJECTS
              |
              v
        EVENT HISTORY
              |
              v
          CHECKPOINT
              |
              v
       RECONCILIATION
              |
              v
        FINAL REPORT
```

### Workflow explanation

1. The application reads its configuration.
2. It connects to the local mock API.
3. It authenticates API requests.
4. It retrieves customer and event records.
5. It processes paginated API responses.
6. It retains the original response data.
7. It validates incoming records.
8. It stores invalid records with their rejection reasons.
9. It inserts new event versions and updates current records when appropriate.
10. It avoids inserting duplicate versions.
11. It prevents older event versions from replacing newer versions.
12. It advances the checkpoint after a successful complete run.
13. It generates reconciliation results.

## 6. Prerequisites

Before running the project, install:

- Python 3.10 or later.
- Git.
- pip.
- Windows PowerShell, Linux terminal, or macOS terminal.

The mock API and SQLite database run locally. No paid external API or hosted database is required.

## 7. Installation and Setup

### Step 1: Clone the repository

```bash
git clone https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion.git
```

Move into the project directory:

```bash
cd yottaflex_api_data_ingestion
```

### Step 2: Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution for the current terminal, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 4: Install project dependencies

```bash
python -m pip install -r requirements.txt
```

Verify the installation:

```bash
python -m pip list
```

## 8. Configuration

The project provides an `.env.example` file with the local configuration values:

```env
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=local-demo-token
DATABASE_PATH=data/ingestion.db
PAGE_SIZE=100
MAX_RETRIES=4
LOOKBACK_SECONDS=3600
MOCK_RECORD_COUNT=250
```

### Windows PowerShell configuration

Set the variables in the terminal:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:API_TOKEN = "local-demo-token"
$env:DATABASE_PATH = "data/ingestion.db"
$env:PAGE_SIZE = "100"
$env:MAX_RETRIES = "4"
$env:LOOKBACK_SECONDS = "3600"
$env:MOCK_RECORD_COUNT = "250"
```

**Note:** These commands set environment variables for the current PowerShell session. If you open another terminal, activate the virtual environment and set the variables again. The `.env.example` file documents the values; it is not automatically loaded unless dotenv support is explicitly configured in the application.

Do not commit real API credentials or private configuration files.

## 9. Running the Application

### Step 1: Start the local mock API

Open Terminal 1 from the project root:

```bash
python -m app.mock_api serve --host 127.0.0.1 --port 8000
```

Keep the server running.

### Step 2: Check API health

Open Terminal 2, activate the virtual environment, set the configuration variables, and run:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

The endpoint should return a successful health response.

### Step 3: Open API documentation

Open the following URL in a browser:

http://127.0.0.1:8000/docs

The interactive documentation can be used to inspect available API endpoints.

### Step 4: Generate expected reconciliation labels

```bash
python -m app.mock_api labels --count 250 --out data/expected_labels.json
```

### Step 5: Execute the ingestion pipeline

```bash
python -m app.pipeline
```

The pipeline fetches source records, validates them, writes the data to SQLite, records run statistics, and advances the checkpoint after a successful complete run.

## 10. Running Automated Tests

Run all tests:

```bash
python -m pytest -v
```

Run a shorter summary:

```bash
python -m pytest -q
```

The test files are:

- `tests/test_validation.py`
- `tests/test_pipeline.py`

The tests cover the implemented validation and pipeline behavior.

Only report the number of passing tests after running the current version of the repository.

## 11. Reconciliation Report

After the pipeline has completed, run:

```bash
python -m app.report --db data/ingestion.db --labels data/expected_labels.json
```

The application generates:

```text
reports/
    reconciliation_report.json
    reconciliation_report.md
```

The reconciliation process checks the consistency of ingested data, including record accounting, customer references, event versions, raw response traceability, and expected results when labels are supplied.

The sample reports committed in `evidence/` provide examples of the report format. They are sample evidence, not automatically proof of a fresh run.

## 12. Performance Benchmark

Run the benchmark:

```bash
python -m app.benchmark --records 100000 --page-size 1000 --out reports/benchmark.json
```

The benchmark compares two customer lookup approaches:

1. Repeated SQL lookups.
2. In-memory customer lookup.

The output includes execution time, throughput, and measured speedup.

This is a local lookup benchmark, not an end-to-end HTTP API performance benchmark.

## 13. Database and Query Inspection

If the SQLite command-line utility is installed, inspect the database:

```bash
sqlite3 data/ingestion.db ".tables"
```

Inspect ingestion runs:

```bash
sqlite3 data/ingestion.db "SELECT * FROM runs;"
```

Inspect current events:

```bash
sqlite3 data/ingestion.db "SELECT * FROM events LIMIT 10;"
```

Inspect rejected records:

```bash
sqlite3 data/ingestion.db "SELECT * FROM rejects LIMIT 10;"
```

Inspect event history:

```bash
sqlite3 data/ingestion.db "SELECT * FROM events_history LIMIT 10;"
```

If SQLite CLI is not installed, use Python's built-in `sqlite3` module to inspect the database.

## 14. Reliability and Data Quality

### Retry handling

The API client is designed to handle temporary request failures and selected HTTP errors.

### Rate limits

HTTP 429 responses are handled using the configured retry behavior.

### Data validation

Incoming data is checked before being stored. Invalid records are retained in the rejects table with their rejection reasons.

### Idempotency

Repeated delivery of an already processed event version should not create another identical history entry.

### Late-arriving records

Older event versions should not overwrite newer current records.

### Checkpoint recovery

The checkpoint advances only after the complete ingestion run succeeds. This allows failed runs to be retried without advancing the ingestion position prematurely.

### Raw response traceability

Original API response data is retained so records can be traced back to the source response.

## 15. Supporting Documentation

Additional technical details are available in:

- [Database Data Dictionary](docs/DATA_DICTIONARY.md)
- [Technical Design Notes](docs/DESIGN_NOTES.md)
- [AI Prompt History and Disclosure](PROMPT_HISTORY.md)

## 16. Sample Evidence

The `evidence/` directory contains sample project outputs:

| Evidence file | Description |
|---|---|
| `test_results.txt` | Saved automated test output |
| `sample_queries_output.txt` | Sample database query results |
| `benchmark.json` | Benchmark output |
| `sample_reconciliation_report.json` | Machine-readable reconciliation report |
| `sample_reconciliation_report.md` | Human-readable reconciliation report |

These files are included to help reviewers understand the project's validation and reporting approach. Re-run the commands above to reproduce the results locally.

## 17. Design Decisions

The project uses a lightweight local architecture:

- Python keeps the implementation straightforward and accessible.
- FastAPI provides a controllable mock API.
- SQLite provides persistent local storage without a separate database server.
- Raw response retention supports traceability.
- Page-level database transactions help prevent partially committed pages.
- Checkpoints support incremental processing.
- Idempotent event-version handling supports safe reruns.
- Automated tests help verify core behavior.

More detailed decisions and trade-offs are documented in [DESIGN_NOTES.md](docs/DESIGN_NOTES.md).

## 18. Limitations and Future Improvements

This project is a locally runnable demonstration, not a complete production deployment.

Possible improvements include:

- Integration with a real third-party API.
- Production-grade secret management.
- PostgreSQL support.
- Structured centralized logging and monitoring.
- Scheduled ingestion and orchestration.
- Continuous integration.
- Larger-scale load and recovery testing.
- Containerized deployment.

The local demo token and mock API are for development and testing only.

## 19. AI Usage Disclosure

The recruitment assignment requires transparent disclosure of AI assistance.

The prompt history and AI-use explanation are maintained in [PROMPT_HISTORY.md](PROMPT_HISTORY.md).

That document should contain the actual prompts used, identify the AI tools involved, and explain which parts were generated or improved with assistance and what was personally reviewed and validated.

Do not claim that no AI tools were used if an AI tool assisted with the project or its documentation.

## 20. How to Reproduce the Project

For a complete local verification:

1. Clone the public GitHub repository.
2. Create and activate the Python virtual environment.
3. Install dependencies from `requirements.txt`.
4. Set the local environment variables.
5. Start the FastAPI mock server.
6. Check the health endpoint.
7. Generate expected labels.
8. Run the automated tests.
9. Run the ingestion pipeline.
10. Generate the reconciliation report.
11. Run the benchmark.
12. Inspect the SQLite database and generated reports.

## 21. Project Submission

**Project:** YottaFlex API Data Ingestion Pipeline

**Candidate:** Sanket Pawar

**GitHub Repository:**

https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion

The repository provides the implementation, installation and execution instructions, technical documentation, test files, sample evidence, and AI-use disclosure required for review.

---

<p align="center">
  <strong>Built as an individual candidate project for the YottaFlex AI Recruitment Drive.</strong>
</p>
