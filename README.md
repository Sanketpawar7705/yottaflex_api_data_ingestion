# YottaFlex API Data Ingestion Pipeline

A Python-based API data ingestion pipeline that retrieves data from an authenticated REST API, processes paginated responses, validates records, and stores the results in SQLite.

The project focuses on reliable data ingestion, error handling, duplicate prevention, incremental processing, and reconciliation reporting.

**GitHub Repository:** [yottaflex_api_data_ingestion](https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion)

---

## 1. Project Overview

The YottaFlex API Data Ingestion Pipeline is designed to collect data from an API and store it in a structured database.

The pipeline handles the main stages of an ingestion workflow, including:

- Authenticated API communication.
- Paginated data retrieval.
- Retry handling for temporary API failures.
- Rate-limit handling.
- Data validation and error handling.
- Raw API response retention.
- Duplicate detection and idempotent storage.
- Incremental ingestion using checkpoints.
- SQLite database storage.
- Reconciliation reporting.
- Automated testing and benchmarking.

A mock API is included to provide a local environment for running and verifying the ingestion workflow.

## 2. Project Objectives

The main objectives of this project are:

1. Retrieve records from an authenticated API.
2. Process API responses page by page.
3. Handle temporary network and server errors.
4. Validate incoming records before storing them.
5. Prevent duplicate records during repeated ingestion.
6. Retain raw API responses for traceability.
7. Support incremental ingestion using checkpoints.
8. Store processed information in SQLite.
9. Generate reconciliation reports.
10. Verify the application through automated tests.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| FastAPI | Local mock API |
| Uvicorn | Running the mock API server |
| Requests | HTTP API communication |
| SQLite | Persistent data storage |
| Pytest | Automated testing |
| Pydantic | Data modelling and validation, where used |
| Git | Version control |
| GitHub | Source code repository |

## 4. Project Structure

The repository is organised into application code, documentation, test cases, and supporting evidence.

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

**Main application modules**

| File | Responsibility |
|---|---|
| `client.py` | Handles communication with the API |
| `config.py` | Loads application configuration |
| `mock_api.py` | Provides the local mock API |
| `pipeline.py` | Coordinates the ingestion workflow |
| `storage.py` | Handles SQLite database operations |
| `validation.py` | Validates incoming records |
| `report.py` | Generates reconciliation reports |
| `benchmark.py` | Runs ingestion performance benchmarks |

## 5. Application Architecture

The pipeline follows a modular design in which API communication, validation, storage, and reporting are handled separately.

```text
                  Mock REST API
                       |
                       |
                API Authentication
                       |
                       |
                Paginated Requests
                       |
                       |
                 Retry Handling
                       |
                       |
                 Data Validation
                       |
              +--------+--------+
              |                 |
         Valid Records      Rejected Records
              |                 |
              |                 |
         SQLite Storage     Reject Storage
              |
              |
       Raw Response Retention
              |
              |
       Checkpoint Management
              |
              |
       Reconciliation Report
```

## 6. Data Ingestion Workflow

The ingestion process follows these steps:

1. Load the application configuration.
2. Establish communication with the mock API.
3. Authenticate API requests using the configured API key.
4. Request records using pagination.
5. Handle temporary API failures and retry eligible requests.
6. Validate the retrieved records.
7. Store raw API responses for traceability.
8. Save valid records in the database.
9. Handle invalid records separately.
10. Maintain ingestion checkpoints.
11. Generate reconciliation reports.

## 7. Database Design

SQLite is used as the persistent storage layer.

The database contains tables for managing ingestion runs, API responses, customer information, events, historical records, rejected records, and checkpoints.

| Table | Purpose |
|---|---|
| `runs` | Stores ingestion run information |
| `raw_responses` | Retains raw API responses |
| `customers` | Stores customer records |
| `events` | Stores processed event records |
| `events_history` | Maintains event history |
| `rejects` | Stores records that fail validation |
| `checkpoints` | Tracks ingestion progress |

For detailed table definitions and field descriptions, refer to [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

## 8. Requirements

Before running the application, make sure the following software is installed:

- Python 3.10 or later.
- Git.
- pip.
- Windows, Linux, or macOS.
- Internet access only if installing dependencies or using an external API.

The included mock API can be run locally.

## 9. Installation and Setup

### Step 1: Clone the repository

```powershell
git clone https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion.git
```

### Step 2: Open the project directory

```powershell
cd yottaflex_api_data_ingestion
```

### Step 3: Create a virtual environment

```powershell
python -m venv .venv
```

### Step 4: Activate the virtual environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 5: Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### Step 6: Install project dependencies

```powershell
python -m pip install -r requirements.txt
```

## 10. Configuration

The repository includes `.env.example` as a reference for the application configuration.

Example configuration:

```env
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=local-demo-token
DATABASE_PATH=data/ingestion.db
PAGE_SIZE=100
MAX_RETRIES=4
LOOKBACK_SECONDS=3600
MOCK_RECORD_COUNT=250
```

The application configuration is read from environment variables. The example file is a template; it is not automatically loaded by Python.

For Windows PowerShell, configure the variables in the terminal where you will run the application:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:API_TOKEN = "local-demo-token"
$env:DATABASE_PATH = "data/ingestion.db"
$env:PAGE_SIZE = "100"
$env:MAX_RETRIES = "4"
$env:LOOKBACK_SECONDS = "3600"
$env:MOCK_RECORD_COUNT = "250"
```

Create the local working directories:

```powershell
New-Item -ItemType Directory -Force data
New-Item -ItemType Directory -Force reports
```

Use a different API token and appropriate configuration when connecting to another API.

## 11. Start the Mock API

The project includes a mock API for local development and testing.

Start the API server:

```powershell
python -m app.mock_api serve --host 127.0.0.1 --port 8000
```

Keep this terminal running.

### Verify the API

Open another PowerShell terminal, activate the virtual environment, and run:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

The API documentation can be accessed at:

```text
http://127.0.0.1:8000/docs
```

The mock API uses the configured API key for authenticated requests.

## 12. Generate Expected Labels

Generate the expected labels used by the reconciliation process:

```powershell
python -m app.mock_api labels --count 250 --out data/expected_labels.json
```

This creates a local reference file for comparing expected and ingested records.

## 13. Run the Ingestion Pipeline

After starting the mock API and configuring the environment variables, run:

```powershell
python -m app.pipeline
```

The pipeline executes the configured ingestion workflow and stores its data in the SQLite database.

The default database path is:

```text
data/ingestion.db
```

## 14. Generate Reconciliation Reports

Run the reconciliation module:

```powershell
python -m app.report --db data/ingestion.db --labels data/expected_labels.json
```

The report files are generated in the `reports/` directory:

```text
reports/
├── reconciliation_report.json
└── reconciliation_report.md
```

The reports can be used to review the reconciliation results and identify differences between expected and ingested records.

## 15. Run Automated Tests

The project includes tests for the ingestion pipeline and validation logic.

Run all tests:

```powershell
python -m pytest -v
```

Run tests with a shorter output:

```powershell
python -m pytest -q
```

To save a fresh test execution log:

```powershell
python -m pytest -v 2>&1 | Tee-Object evidence\test_results.txt
```

The saved test log should reflect the actual execution result. Do not modify it to show tests passing if they failed.

## 16. Run the Benchmark

The benchmark module can be used to evaluate ingestion performance with a larger number of records.

Example:

```powershell
python -m app.benchmark --records 100000 --page-size 1000 --out reports/benchmark.json
```

The benchmark output is saved to:

```text
reports/benchmark.json
```

The benchmark configuration can be adjusted to test different record counts and page sizes.

## 17. Database Verification

The SQLite database can be inspected to verify stored records.

If the SQLite command-line utility is installed, use:

```powershell
sqlite3 data/ingestion.db ".tables"
```

View ingestion runs:

```powershell
sqlite3 data/ingestion.db "SELECT * FROM runs;"
```

View event records:

```powershell
sqlite3 data/ingestion.db "SELECT * FROM events LIMIT 10;"
```

View rejected records:

```powershell
sqlite3 data/ingestion.db "SELECT * FROM rejects LIMIT 10;"
```

View event history:

```powershell
sqlite3 data/ingestion.db "SELECT * FROM events_history LIMIT 10;"
```

These queries are intended for local inspection. The SQLite command-line utility is optional; the application itself uses Python's SQLite support.

## 18. Error Handling and Reliability

The ingestion workflow is designed to handle common API and data-processing problems.

The implementation includes mechanisms for:

- Handling temporary network failures.
- Retrying eligible HTTP errors.
- Managing API rate limits.
- Handling unsuccessful API responses.
- Validating incoming data.
- Separating rejected records from valid records.
- Preventing duplicate data insertion.
- Maintaining checkpoints for incremental processing.
- Retaining raw responses for traceability.

Authentication errors and other non-retryable failures should be handled separately from temporary server or network errors.

## 19. Idempotency and Incremental Ingestion

Idempotency is important when an ingestion job is executed more than once.

The project uses database-level storage logic to avoid creating duplicate records during repeated ingestion.

Checkpoints are used to track ingestion progress and support incremental processing.

This approach helps reduce unnecessary reprocessing and makes the workflow more reliable when jobs are restarted.

## 20. Design Decisions and Trade-offs

The project uses a modular structure to keep API communication, validation, storage, and reporting responsibilities separate.

Some key design considerations include:

| Decision | Reason |
|---|---|
| SQLite | Provides lightweight persistent storage without requiring a separate database server |
| Mock API | Allows local execution and testing without depending on an external service |
| Pagination | Supports processing records in manageable batches |
| Retry handling | Helps recover from temporary API failures |
| Raw response retention | Supports traceability and troubleshooting |
| Checkpoints | Support incremental ingestion |
| Validation | Prevents invalid records from entering the main data tables |
| Reconciliation reports | Help compare expected and ingested data |

More detailed implementation decisions and trade-offs are documented in [DESIGN_NOTES.md](docs/DESIGN_NOTES.md).

## 21. Evidence and Results

The `evidence/` directory contains supporting files related to the project.

```text
evidence/
├── benchmark.json
├── sample_queries_output.txt
├── sample_reconciliation_report.json
├── sample_reconciliation_report.md
└── test_results.txt
```

These files provide examples of benchmark output, database queries, reconciliation reports, and test execution results.

For accurate evaluation, the evidence should correspond to actual application runs.

## 22. Known Limitations and Future Improvements

The current implementation is intended as a local API ingestion project.

Possible future improvements include:

- Supporting additional external API integrations.
- Adding structured application logging.
- Improving monitoring and alerting.
- Supporting PostgreSQL for larger workloads.
- Adding configurable ingestion schedules.
- Improving parallel processing where appropriate.
- Adding automated CI workflows.
- Expanding integration and failure-recovery tests.

These are potential improvements rather than claims about features already implemented.

## 23. Repository and Project Files

| File | Description |
|---|---|
| `README.md` | Project overview and setup instructions |
| `PROMPT_HISTORY.md` | Development prompt history and assistance disclosure |
| `docs/DATA_DICTIONARY.md` | Database documentation |
| `docs/DESIGN_NOTES.md` | Design decisions and technical trade-offs |
| `requirements.txt` | Python dependencies |
| `pytest.ini` | Pytest configuration |
| `.env.example` | Example application configuration |
| `.gitignore` | Files excluded from version control |

## 24. Running the Project – Quick Reference

After completing the installation and configuration steps, the main workflow is:

**Terminal 1 – Start the API**

```powershell
python -m app.mock_api serve --host 127.0.0.1 --port 8000
```

**Terminal 2 – Run the project**

```powershell
python -m app.mock_api labels --count 250 --out data/expected_labels.json

python -m app.pipeline

python -m app.report --db data/ingestion.db --labels data/expected_labels.json

python -m pytest -v
```

For a benchmark run:

```powershell
python -m app.benchmark --records 100000 --page-size 1000 --out reports/benchmark.json
```

## 25. Author

**Sanket Pawar**

GitHub: [Sanketpawar7705](https://github.com/Sanketpawar7705)

Project: [YottaFlex API Data Ingestion Pipeline](https://github.com/Sanketpawar7705/yottaflex_api_data_ingestion)

---

**Note:** This repository is intended to demonstrate API integration, data ingestion, validation, database storage, and reconciliation concepts through a locally executable Python application.
