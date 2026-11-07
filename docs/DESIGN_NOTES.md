# Design and trade-offs
1. **Offset pagination** is fine for a static mock; a mutable production API needs cursors/snapshots. The lookback overlap softens page shifts.
2. **At-least-once fetch + idempotent load.** Re-reading data is always safe: `(event_id, updated_at)` identifies a version, so repeats are counted as duplicates.
3. **Current table + history table.** `events` answers "what is true now"; `events_history` keeps every version, so nothing is silently overwritten.
4. **Checkpoint after the run, not per page.** Simple and provably restartable; the cost is that a failed run re-reads pages that were already loaded (they become duplicates).
5. **Lookback window (1 h)** catches late arrivals cheaply; anything older needs `--since` (explicit backfill). The watermark never moves backwards and is built only from valid rows, and records dated > 1 day ahead are rejected so one bad timestamp cannot freeze it.
6. **Quarantine instead of drop.** Bad records go to `rejects` with reason and content, traceable to the raw page via `source_file`.
7. **Schema change policy.** Additive field → accept and count. Required field missing from ≥ 50 % of a page → fail the run before loading (raw page is kept). One bad record is a data-quality issue; many is a contract break.
8. **Retries only where they can help** (429, 5xx, network, truncated JSON). Auth and other 4xx errors fail fast.
9. **Raw responses in SQLite** keep the project self-contained; production would use object storage.
10. **Customers loaded first**; if that fails, the run fails (events cannot be checked against stale reference data).
