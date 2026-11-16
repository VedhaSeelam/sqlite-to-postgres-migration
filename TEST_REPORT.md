# Test Report

- **Date:** 2026-11-16
- **Environment:** Python 3.14.4, PostgreSQL 17.12, Windows
- **How to reproduce:** `python test_migration.py`

| ID | Type | Test | Expected | Actual | Result |
|---|---|---|---|---|---|
| F1 | Functional | Row count matches for organiser | 5 | 5 | PASS |
| F2 | Functional | Row count matches for venue | 8 | 8 | PASS |
| F3 | Functional | Row count matches for category | 6 | 6 | PASS |
| F4 | Functional | Row count matches for customer | 150 | 150 | PASS |
| F5 | Functional | Row count matches for event | 30 | 30 | PASS |
| F6 | Functional | Row count matches for ticket_type | 90 | 90 | PASS |
| F7 | Functional | Row count matches for booking | 400 | 400 | PASS |
| F8 | Functional | Row count matches for payment | 357 | 357 | PASS |
| F9 | Functional | No orphaned foreign keys in target (6 relationships checked) | 0 | 0 | PASS |
| F10 | Functional | Total of paid payments matches | 55969.13 | 55969.13 | PASS |
| F11 | Functional | Bookings per event (top 5) identical | 5 rows | 5 rows | PASS |
| F12 | Functional | Paid revenue per category identical | 6 rows | 6 rows | PASS |
| F13 | Functional | Customers with 3+ bookings identical | 76 rows | 76 rows | PASS |
| F14 | Functional | New INSERT after migration gets a fresh id (sequence reset worked) | insert succeeds | insert succeeds | PASS |
| F15 | Functional | No duplicate customer emails in target | 0 | 0 | PASS |
| N1 | Non-functional (performance) | Small dataset migrates in under 30 s | < 30 s | 0.30 s | PASS |
| N2 | Non-functional (reliability) | Re-running without --reset does not duplicate data | refused safely, counts unchanged | refused safely, counts unchanged: True | PASS |
| N3 | Non-functional (data integrity) | Source with an orphaned booking is rejected before the target is touched | pre-flight stopped it, counts unchanged | pre-flight stopped it, counts unchanged: True | PASS |
| N4 | Non-functional (reliability) | Row that breaks a stricter target rule triggers a full rollback (even with --reset) | rolled back, original target data intact | target rejected row, rolled back, counts unchanged: True | PASS |
| N5 | Non-functional (performance/scalability) | 25x dataset (25,800 rows) migrates in under 60 s with matching counts | < 60 s, counts match | 0.77 s, counts match: True | PASS |

**Summary:** 20 of 20 tests passed.
