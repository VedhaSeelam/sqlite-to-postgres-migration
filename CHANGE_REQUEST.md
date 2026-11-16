# Change Request: Migrate Event-Booking Database from SQLite to PostgreSQL

| Field | Detail |
|---|---|
| Change ID | CR-001 |
| Title | Move the event-booking database from SQLite to PostgreSQL |
| Requested by | Vedha Sree Seelam |
| Date raised | 16 Nov 2026 |
| Change type | Normal (planned, scheduled, needs approval) |
| Priority | Medium |
| Status | Approved |

## 1. Description of the change

Move the 8-table event-booking database (Event, Booking, Payment, Venue and related tables) from a single-file SQLite database (`source.db`) to a PostgreSQL database, using the `migrate.py` script. The application data and structure stay the same. Only the database engine changes.

## 2. Reason for the change

- SQLite is a single-file database and is not suited to many users at once.
- PostgreSQL supports concurrent access, stricter data types and enforced foreign keys.
- The migration also tests the approach in the migration plan (data mapping, load order, rollback, cutover) before it is used on a larger system.

## 3. Scope

**In scope:** all 8 tables and their data, the PostgreSQL schema (`schema_postgres.sql`), the migration script, and the automated tests.

**Out of scope:** changes to the table design, new features, and hosting or deployment of PostgreSQL.

## 4. Impact assessment

| Area | Impact |
|---|---|
| Data | All rows are copied. Source data is read-only during migration and is not modified. |
| Users / systems | Anything reading `source.db` must be pointed at PostgreSQL after cutover. |
| Downtime | Writes to the source database must pause between the final backup and cutover. |
| Risk level | Low to medium (see section 5). |

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bad or orphaned data in the source | Pre-flight integrity check runs before any data is loaded. |
| Tables loaded in the wrong order, breaking foreign keys | Parents-first load order is built into the script. |
| Script fails part way, leaving partial data | Whole load runs in a single transaction that rolls back on any error. |
| Data differs after migration | Automated tests compare row counts, foreign key integrity, payment totals and query results. |
| Script is run twice by mistake | Re-run behaviour is tested so a repeat run is safe. |

## 6. Implementation plan

1. Back up `source.db`.
2. Create the target database and apply `schema_postgres.sql`.
3. Run the pre-flight integrity check on the source data.
4. Run `migrate.py` (single transaction).
5. Run `test_migration.py` and review the results against `docs/TEST_REPORT.md`.
6. Complete the cutover checklist in the migration plan and repoint the application.

**Planned date:** 16 Nov 2026

## 7. Rollback plan

- **If the migration script fails:** the transaction rolls back automatically and the target stays unchanged. Fix the cause and re-run.
- **If tests fail after the load:** do not cut over. Drop and recreate the target database, then re-run.
- **If a problem is found after cutover:** point the application back to the untouched `source.db` backup and investigate.

**Rollback trigger:** any failed test, or any mismatch in row counts or payment totals.

## 8. Communication

| Who | What they are told | When |
|---|---|---|
| Project owner and reviewer | Change request for approval | Before the change |
| Anyone using the database | Planned cutover date and expected pause in writes | Before the change |
| Project owner and reviewer | Outcome, test results and any issues | After the change |

## 9. Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| Requester | Vedha Sree Seelam | Submitted | 16 Nov 2026 |
| Approver | Vedha Sree Seelam (project owner) | Approved | 16 Nov 2026 |

## 10. Post-implementation review

To be completed after cutover: was the change successful, were there any issues, and what should be done differently next time. See `docs/STATUS_REPORT.md` for current progress.
