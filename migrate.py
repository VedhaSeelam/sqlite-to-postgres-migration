"""Migrate the event-booking database from SQLite (source) to PostgreSQL (target).

Usage:
    python migrate.py                # fails safely if the target tables already exist
    python migrate.py --reset        # drops the target tables first, then migrates

Target connection comes from the DATABASE_URL environment variable (never hard-code
passwords), e.g.  postgresql://postgres:YOUR_PASSWORD@localhost:5432/event_booking_target

Design (see docs/MIGRATION_PLAN.md):
  1. Pre-flight: refuse to start if the SOURCE has broken foreign keys.
  2. One transaction: create schema, load tables parents-first, fix identity sequences.
  3. Any error -> ROLLBACK, so the target is never left half-migrated.
"""
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

HERE = Path(__file__).parent
SCHEMA_PG = HERE / "schema_postgres.sql"

# LOAD ORDER matters: a child table can only be loaded after the table it references.
# (table name, primary key column)
TABLES = [
    ("organiser", "organiser_id"),
    ("venue", "venue_id"),
    ("category", "category_id"),
    ("customer", "customer_id"),
    ("event", "event_id"),
    ("ticket_type", "ticket_type_id"),
    ("booking", "booking_id"),
    ("payment", "payment_id"),
]


class MigrationError(Exception):
    """Raised when the migration must stop before changing the target."""


def preflight(src: sqlite3.Connection) -> None:
    """Check the source is clean BEFORE touching the target."""
    violations = src.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise MigrationError(
            f"Source has {len(violations)} foreign key violation(s); first: {violations[0]}. "
            "Nothing was changed in the target."
        )


def clean(value):
    """Transform one value on the way across (SQLite REAL -> NUMERIC needs rounding)."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, float):
        return round(value, 2)
    return value


def run(sqlite_path, dsn, reset=False, log=print) -> dict:
    """Run the migration. Returns {'rows': {table: n}, 'seconds': float}."""
    started = time.perf_counter()
    src = sqlite3.connect(sqlite_path)
    preflight(src)

    pg = psycopg2.connect(dsn)          # autocommit is off: everything below is ONE transaction
    rows_loaded = {}
    try:
        with pg.cursor() as cur:
            if reset:
                for table, _ in reversed(TABLES):        # children first when dropping
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                log("Reset: dropped existing target tables")
            cur.execute(SCHEMA_PG.read_text())
            log("Created target schema")

            for table, id_col in TABLES:
                cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
                data = [tuple(clean(v) for v in r)
                        for r in src.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY {id_col}")]
                if data:
                    execute_values(cur, f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s", data)
                # Rows were inserted with explicit ids, so move the identity counter past them,
                # otherwise the next normal INSERT would clash with an existing id.
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{id_col}'), "
                    f"COALESCE(MAX({id_col}), 1)) FROM {table}"
                )
                rows_loaded[table] = len(data)
                log(f"Loaded {table:<12} {len(data):>7} rows")
        pg.commit()
        log("COMMIT: migration complete")
    except Exception:
        pg.rollback()
        log("ROLLBACK: error during migration, target left unchanged")
        raise
    finally:
        pg.close()
        src.close()
    return {"rows": rows_loaded, "seconds": time.perf_counter() - started}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(HERE / "source.db"))
    ap.add_argument("--reset", action="store_true", help="drop target tables first")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("Set the DATABASE_URL environment variable first (see README).")
        return 2
    try:
        result = run(args.source, dsn, reset=args.reset)
    except MigrationError as e:
        print(f"STOPPED: {e}")
        return 1
    except psycopg2.errors.DuplicateTable:
        print("STOPPED: target tables already exist. Re-run with --reset to replace them.")
        return 1
    print(f"Done in {result['seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
