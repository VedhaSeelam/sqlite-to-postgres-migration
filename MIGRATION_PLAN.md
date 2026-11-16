# Migration Plan: Event Booking Database (SQLite to PostgreSQL)

**Author:** Vedha Sree Seelam  |  **Status:** Executed in a local test environment

## 1. Purpose and scope
Migrate the event-booking database (8 tables: organiser, venue, category, customer, event, ticket_type, booking, payment) from a file-based SQLite database to PostgreSQL, simulating the move of an application's data to new infrastructure.

**In scope:** schema conversion, data load, validation, rollback.
**Out of scope:** application code changes, user access setup, production hosting.

## 2. Source and target
| | Source | Target |
|---|---|---|
| Platform | SQLite (single file) | PostgreSQL |
| Typing | Loose; dates as TEXT, money as REAL | Strict; DATE/TIMESTAMP, NUMERIC(10,2) |
| Rules | Foreign keys and uniqueness only | Adds CHECK constraints (e.g. quantity > 0, valid status values) |
| IDs | INTEGER PRIMARY KEY (rowid) | IDENTITY columns with sequences |

## 3. Data mapping
| SQLite | PostgreSQL | Transformation |
|---|---|---|
| INTEGER (ids) | INTEGER IDENTITY | Loaded with explicit ids; sequence reset afterwards |
| TEXT (names, email) | VARCHAR(n) | Trim whitespace |
| TEXT 'YYYY-MM-DD' | DATE | Cast on insert |
| TEXT 'YYYY-MM-DD HH:MM:SS' | TIMESTAMP | Cast on insert |
| REAL (prices, amounts) | NUMERIC(10,2) | Round to 2 decimal places |
| TEXT status/method | VARCHAR + CHECK | Validated against allowed values |

## 4. Load order
Parents before children, because of foreign keys:
organiser, venue, category, customer, event, ticket_type, booking, payment.
Tables are dropped in the reverse order.

## 5. Approach
1. **Pre-flight check:** run `PRAGMA foreign_key_check` on the source. Stop if anything is broken.
2. **Single transaction:** create the target schema, load all tables, reset identity sequences, then COMMIT.
3. **Validate:** row counts, orphaned keys, financial totals, and sample query comparison (`test_migration.py`).

## 6. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Source data breaks the stricter target rules | Whole migration runs in one transaction and rolls back on any error (tested) |
| Orphaned records in the source | Pre-flight foreign key check stops before the target is touched (tested) |
| Money rounding differences (REAL to NUMERIC) | Round on load; compare payment totals after migration (tested) |
| Duplicate data if the script is run twice | Script refuses to run if target tables exist unless `--reset` is used (tested) |
| New inserts clash with migrated ids | Identity sequences reset after load (tested) |
| Slow load on larger data | Batch inserts; timed on a 25x dataset (tested) |
| Special characters in the database password break the connection string | Use the key=value connection format, which handles any password, and confirm the connection works before running the migration |
| Database password accidentally committed to GitHub | Keep the password in an environment variable (`DATABASE_URL`), never in the code, and exclude local files with `.gitignore` |

## 7. Rollback
Because schema and data changes happen in one transaction, a failed run leaves the target exactly as it was. After a successful run, rollback means re-running with `--reset` or dropping the target database. The source file is never modified.

## 8. Cutover checklist
- [ ] Source backed up (copy `source.db`)
- [ ] Pre-flight check passes
- [ ] Target database created and reachable (`DATABASE_URL` set)
- [ ] Migration run completes with COMMIT
- [ ] `test_migration.py` shows all tests passing
- [ ] Application connection string switched to PostgreSQL
- [ ] Smoke test of key user flows (browse events, book, pay)
- [ ] Source kept read-only for a fallback period

## 9. Assumptions
Personal learning project using generated sample data; no real customer data is involved. Cutover steps involving an application are described but not executed.
