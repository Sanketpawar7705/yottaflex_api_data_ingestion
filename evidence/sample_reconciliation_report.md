# Reconciliation report

**Overall: PASS**

| Result | Check | Detail |
|---|---|---|
| PASS | every successful run: received = inserted + updated + duplicates + late_ignored + rejected | all runs balance |
| PASS | referential integrity: every event has a customer | orphans=0 |
| PASS | events holds exactly one row per event in history | events=231 history_distinct=231 |
| PASS | events always holds the newest version | stale=0 |
| PASS | every reject is traceable to a retained raw response | untraceable=0 |
| PASS | raw responses match their SHA-256 | ok |
| PASS | labels: distinct valid events | actual=231 expected=231 |
| PASS | labels: SUM(amount_minor) | actual=28561 expected=28561 |
| PASS | labels: rejects by category | actual={'future_timestamp': 3, 'invalid_amount': 5, 'invalid_customer_ref': 2, 'invalid_timestamp': 3, 'missing_field': 3} expected={'future_timestamp |
| PASS | labels: counters of the first full run | match |
