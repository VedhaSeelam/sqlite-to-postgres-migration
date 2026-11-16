"""Functional and non-functional tests for migrate.py. Writes docs/TEST_REPORT.md.

Usage:  python test_migration.py      (needs DATABASE_URL, see README)
"""
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg2

import create_source_db
import migrate

HERE = Path(__file__).parent
DSN = os.environ.get("DATABASE_URL")
SOURCE = HERE / "source.db"
quiet = lambda *_: None          # silence migrate.py logging inside tests
results = []                     # (id, type, description, expected, actual, passed)


def record(tid, kind, desc, expected, actual, passed):
    results.append((tid, kind, desc, str(expected), str(actual), bool(passed)))
    print(f"[{'PASS' if passed else 'FAIL'}] {tid} {desc}")


def pg_scalar(sql):
    with psycopg2.connect(DSN) as c, c.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def pg_rows(sql):
    with psycopg2.connect(DSN) as c, c.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def lite_rows(sql, path=SOURCE):
    db = sqlite3.connect(path)
    try:
        return db.execute(sql).fetchall()
    finally:
        db.close()


def norm(rows):
    """Make SQLite and PostgreSQL results comparable (Decimal -> float, 2 dp)."""
    return [tuple(round(float(v), 2) if isinstance(v, (Decimal, float)) else v for v in r) for r in rows]


def target_counts():
    return {t: pg_scalar(f"SELECT COUNT(*) FROM {t}") for t, _ in migrate.TABLES}


def main():
    if not DSN:
        print("Set DATABASE_URL first (see README).")
        return 2
    create_source_db.build(SOURCE, 1.0)

    # ---- Functional tests -------------------------------------------------
    res = migrate.run(SOURCE, DSN, reset=True, log=quiet)
    for i, (table, _) in enumerate(migrate.TABLES, 1):
        src_n = lite_rows(f"SELECT COUNT(*) FROM {table}")[0][0]
        tgt_n = pg_scalar(f"SELECT COUNT(*) FROM {table}")
        record(f"F{i}", "Functional", f"Row count matches for {table}", src_n, tgt_n, src_n == tgt_n)

    fks = [("booking", "customer_id", "customer", "customer_id"),
           ("booking", "event_id", "event", "event_id"),
           ("booking", "ticket_type_id", "ticket_type", "ticket_type_id"),
           ("payment", "booking_id", "booking", "booking_id"),
           ("event", "venue_id", "venue", "venue_id"),
           ("ticket_type", "event_id", "event", "event_id")]
    orphans = sum(pg_scalar(f"SELECT COUNT(*) FROM {c} x LEFT JOIN {p} y ON x.{cc} = y.{pc} WHERE y.{pc} IS NULL")
                  for c, cc, p, pc in fks)
    record("F9", "Functional", "No orphaned foreign keys in target (6 relationships checked)", 0, orphans, orphans == 0)

    s = lite_rows("SELECT ROUND(SUM(amount),2) FROM payment WHERE status='paid'")[0][0]
    t = float(pg_scalar("SELECT SUM(amount) FROM payment WHERE status='paid'"))
    record("F10", "Functional", "Total of paid payments matches", s, round(t, 2), abs(s - t) < 0.01)

    queries = {
        "F11": ("Bookings per event (top 5) identical",
                "SELECT event_id, COUNT(*) FROM booking GROUP BY event_id ORDER BY 2 DESC, 1 LIMIT 5"),
        "F12": ("Paid revenue per category identical",
                "SELECT c.name, ROUND(SUM(p.amount),2) FROM payment p JOIN booking b ON b.booking_id=p.booking_id "
                "JOIN event e ON e.event_id=b.event_id JOIN category c ON c.category_id=e.category_id "
                "WHERE p.status='paid' GROUP BY c.name ORDER BY c.name"),
        "F13": ("Customers with 3+ bookings identical",
                "SELECT customer_id, COUNT(*) FROM booking GROUP BY customer_id HAVING COUNT(*) >= 3 ORDER BY customer_id"),
    }
    for tid, (desc, sql) in queries.items():
        a, b = norm(lite_rows(sql)), norm(pg_rows(sql))
        record(tid, "Functional", desc, f"{len(a)} rows", f"{len(b)} rows", a == b)

    # Identity sequences: a normal INSERT after migration must not clash with migrated ids.
    try:
        with psycopg2.connect(DSN) as c, c.cursor() as cur:
            cur.execute("INSERT INTO category (name) VALUES ('Test category')")
            cur.execute("DELETE FROM category WHERE name = 'Test category'")
        ok = True
    except psycopg2.Error:
        ok = False
    record("F14", "Functional", "New INSERT after migration gets a fresh id (sequence reset worked)",
           "insert succeeds", "insert succeeds" if ok else "id clash", ok)

    dupes = pg_scalar("SELECT COUNT(*) FROM (SELECT email FROM customer GROUP BY email HAVING COUNT(*) > 1) d")
    record("F15", "Functional", "No duplicate customer emails in target", 0, dupes, dupes == 0)

    # ---- Non-functional tests --------------------------------------------
    record("N1", "Non-functional (performance)", "Small dataset migrates in under 30 s",
           "< 30 s", f"{res['seconds']:.2f} s", res["seconds"] < 30)

    before = target_counts()
    try:
        migrate.run(SOURCE, DSN, reset=False, log=quiet)
        outcome = "ran (duplicated or overwrote data)"
    except psycopg2.errors.DuplicateTable:
        outcome = "refused safely"
    record("N2", "Non-functional (reliability)", "Re-running without --reset does not duplicate data",
           "refused safely, counts unchanged", f"{outcome}, counts unchanged: {target_counts() == before}",
           outcome == "refused safely" and target_counts() == before)

    tmp = Path(tempfile.mkdtemp())
    try:
        bad = tmp / "bad_fk.db"
        shutil.copy(SOURCE, bad)
        db = sqlite3.connect(bad)
        db.execute("INSERT INTO booking VALUES (999999, 99999, 1, 1, 1, '2026-09-01 10:00:00', 'confirmed')")
        db.commit(); db.close()
        try:
            migrate.run(bad, DSN, reset=True, log=quiet)
            outcome = "migrated bad data"
        except migrate.MigrationError:
            outcome = "pre-flight stopped it"
        record("N3", "Non-functional (data integrity)", "Source with an orphaned booking is rejected before the target is touched",
               "pre-flight stopped it, counts unchanged", f"{outcome}, counts unchanged: {target_counts() == before}",
               outcome == "pre-flight stopped it" and target_counts() == before)

        strict = tmp / "bad_rule.db"
        shutil.copy(SOURCE, strict)
        db = sqlite3.connect(strict)
        db.execute("UPDATE booking SET quantity = 0 WHERE booking_id = 1")   # SQLite allows it, PostgreSQL CHECK does not
        db.commit(); db.close()
        try:
            migrate.run(strict, DSN, reset=True, log=quiet)
            outcome = "migrated bad data"
        except psycopg2.errors.CheckViolation:
            outcome = "target rejected row, rolled back"
        record("N4", "Non-functional (reliability)", "Row that breaks a stricter target rule triggers a full rollback (even with --reset)",
               "rolled back, original target data intact", f"{outcome}, counts unchanged: {target_counts() == before}",
               outcome == "target rejected row, rolled back" and target_counts() == before)

        big = tmp / "big.db"
        counts = create_source_db.build(big, 25.0)
        r2 = migrate.run(big, DSN, reset=True, log=quiet)
        total = sum(counts.values())
        record("N5", "Non-functional (performance/scalability)",
               f"25x dataset ({total:,} rows) migrates in under 60 s with matching counts",
               "< 60 s, counts match", f"{r2['seconds']:.2f} s, counts match: {r2['rows'] == counts}",
               r2["seconds"] < 60 and r2["rows"] == counts)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        migrate.run(SOURCE, DSN, reset=True, log=quiet)      # leave the target in its normal state

    write_report()
    failed = [r for r in results if not r[5]]
    print(f"\n{len(results) - len(failed)}/{len(results)} tests passed. Report: docs/TEST_REPORT.md")
    return 1 if failed else 0


def write_report():
    pg_version = pg_scalar("SHOW server_version")
    lines = [
        "# Test Report",
        "",
        f"- **Date:** {date.today().isoformat()}",
        f"- **Environment:** Python {platform.python_version()}, PostgreSQL {pg_version}, {platform.system()}",
        "- **How to reproduce:** `python test_migration.py`",
        "",
        "| ID | Type | Test | Expected | Actual | Result |",
        "|---|---|---|---|---|---|",
    ]
    for tid, kind, desc, exp, act, ok in results:
        lines.append(f"| {tid} | {kind} | {desc} | {exp} | {act} | {'PASS' if ok else 'FAIL'} |")
    passed = sum(r[5] for r in results)
    lines += ["", f"**Summary:** {passed} of {len(results)} tests passed.", ""]
    (HERE / "docs" / "TEST_REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())