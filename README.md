# SQLite to PostgreSQL Migration (Event Booking Database)

A small end-to-end data migration project: move an 8-table event-booking database from SQLite to PostgreSQL using Python, with a migration plan, automated functional and non-functional tests, and a test report.

Built as a personal learning project to practise migration design, build and testing. It uses generated sample data only.

## What it demonstrates
- **Migration design:** data mapping, load order, risks, rollback and cutover checklist ([docs/MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md))
- **Migration build:** Python script with a pre-flight check, single-transaction load and automatic rollback
- **Functional testing:** row counts, foreign key integrity, financial totals, identical query results
- **Non-functional testing:** performance on a 25x dataset, safe re-runs, bad-data handling, rollback ([docs/TEST_REPORT.md](docs/TEST_REPORT.md))

## Project structure
| File | Purpose |
|---|---|
| `schema_sqlite.sql` | Source schema |
| `schema_postgres.sql` | Target schema (stricter types and rules) |
| `create_source_db.py` | Generates the source database with fake data |
| `migrate.py` | The migration |
| `test_migration.py` | Runs all tests and writes the test report |
| `docs/` | Migration plan and test report |

## Setup
1. Install Python 3.10+ and PostgreSQL (the installer includes pgAdmin).
2. Install the dependency: `pip install -r requirements.txt`
3. Create an empty database in pgAdmin (or run `CREATE DATABASE event_booking_target;`).
4. Set the connection string (replace YOUR_PASSWORD; never commit real passwords):
   - Windows PowerShell: `$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/event_booking_target"`
   - Mac/Linux: `export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/event_booking_target"`

## Run
```
python create_source_db.py      # build the source database
python migrate.py --reset       # migrate to PostgreSQL
python test_migration.py        # run the tests and write docs/TEST_REPORT.md
```
## What I learned
- Migration is mostly about order and safety, not copying rows. Tables have to load parents before children because of foreign keys, and running everything in one transaction means a failure leaves the target untouched.
- The new system is stricter than the old one. SQLite accepted a booking with quantity 0, but PostgreSQL's CHECK rule rejected it. Testing this showed me that the rollback also protects existing data when the script is run with --reset.
- Loading explicit ids breaks the auto-increment counter. I had to reset the identity sequences after loading, otherwise the next normal insert would clash with a migrated id.
- Testing needs more than row counts. I also compared totals and query results between both databases, checked for orphaned keys, and tested bad data and re-runs.
- Setup problems were a real part of the work. My Python had no pip and wasn't on PATH, and a password with special characters broke the URL-style connection string, so I switched to the key=value format. Reading the error message carefully each time was what fixed them.
- Next time I would test on a much larger dataset, write the migration log to a file, and try it against a hosted PostgreSQL instead of a local one.

## Limitations
- Sample data only; not tuned for very large databases (the 25x test is about 26,000 rows).
- Application cut-over is described in the plan but not executed.
