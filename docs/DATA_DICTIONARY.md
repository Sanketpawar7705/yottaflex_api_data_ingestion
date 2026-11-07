# Data dictionary
Timestamps: ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ`. Money: `amount_minor` integer (12.34 → 1234). Names: snake_case.

## Source API (X-API-Key header)
`GET /customers?page&page_size` and `GET /records?page&page_size&updated_after` →
`{"page","page_size","total","total_pages","records":[...]}`.

| field (records) | type | rule |
|---|---|---|
| event_id | string | required, non-empty, key of the event |
| customer_id | string | required, must exist in customers (referential integrity) |
| amount | number | required, ≥ 0, at most 2 decimals, not boolean/string/null |
| currency | string | required, 3 uppercase letters |
| status | string | pending / completed / cancelled |
| event_time, updated_at | string | ISO-8601 with timezone; updated_at ≤ now + 1 day |

## Target tables (SQLite)
| table | key | content |
|---|---|---|
| customers | customer_id | reference data (name, country), run_id, source_file |
| events | event_id (FK customer_id → customers) | newest valid version; amount, amount_minor, currency, status, event_time, updated_at, source_file, run_id, ingested_at |
| events_history | (event_id, updated_at) | every distinct version received (change history, never overwritten) |
| rejects | reject_key = sha256(reason + content) | reason `category[:detail]`, raw_record, run_id, source_file, seen_count, last_run_id |
| raw_responses | source_file `<run_id>/<endpoint>/page_NNNN` | untouched response text, sha256, bytes, record_count, status |
| runs | run_id | status, started_at, ended_at, since, pages, received, inserted, updated, duplicates, late_ignored, rejected, unexpected_field_records, retries, rate_limited, duration_seconds, error |
| checkpoints | source | last_updated_at (watermark) |

Derived fields: `amount_minor`, normalised UTC timestamps. Nullability: only `customers.name/country`, `rejects.event_id`, run end fields may be NULL.

Reject categories: malformed_record, missing_field, invalid_event_id, invalid_customer_ref, invalid_amount, invalid_currency,
invalid_status, invalid_timestamp, future_timestamp.
