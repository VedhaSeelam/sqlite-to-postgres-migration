"""Create the SOURCE database (SQLite) and fill it with fake event-booking data.

Usage:
    python create_source_db.py                      # small dataset -> source.db
    python create_source_db.py --scale 25 --out big.db   # 25x bigger, for timing tests
"""
import argparse
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
FIRST = ["Ava", "Liam", "Noah", "Mia", "Zoe", "Ethan", "Isla", "Lucas", "Priya", "Arjun",
         "Chloe", "Oliver", "Sofia", "Kai", "Maya", "Leo", "Ruby", "Jack", "Anika", "Ben"]
LAST = ["Nguyen", "Smith", "Patel", "Wong", "Brown", "Singh", "Kim", "Taylor", "Lee", "Chen",
        "Wilson", "Khan", "Martin", "Rossi", "Silva", "Jones", "Das", "Park", "Reddy", "Clark"]
SUBURBS = ["Parramatta", "Newtown", "Bondi", "Manly", "Chatswood", "Surry Hills", "Redfern", "Ultimo"]
CATEGORIES = ["Music", "Sport", "Tech", "Food", "Comedy", "Theatre"]
TICKETS = [("General", 1.0, 200), ("VIP", 2.2, 40), ("Student", 0.7, 80)]
METHODS = ["card", "paypal", "bank_transfer"]


def build(out: Path, scale: float, seed: int = 42) -> dict:
    rnd = random.Random(seed)                 # fixed seed -> same data every run
    if out.exists():
        out.unlink()
    db = sqlite3.connect(out)
    db.executescript((HERE / "schema_sqlite.sql").read_text())

    n_org, n_ven = 5, 8
    n_cust, n_evt = int(150 * scale), int(30 * scale)
    n_book = int(400 * scale)

    db.executemany("INSERT INTO organiser VALUES (?,?,?)",
                   [(i, f"Organiser {i}", f"org{i}@example.com") for i in range(1, n_org + 1)])
    db.executemany("INSERT INTO venue VALUES (?,?,?,?)",
                   [(i, f"Venue {i}", SUBURBS[i - 1], rnd.choice([150, 300, 500, 1000]))
                    for i in range(1, n_ven + 1)])
    db.executemany("INSERT INTO category VALUES (?,?)", list(enumerate(CATEGORIES, 1)))
    db.executemany("INSERT INTO customer VALUES (?,?,?,?)",
                   [(i, rnd.choice(FIRST), rnd.choice(LAST), f"customer{i}@example.com")
                    for i in range(1, n_cust + 1)])

    start = datetime(2026, 12, 1)
    events, tickets = [], []
    for e in range(1, n_evt + 1):
        price = round(rnd.uniform(15, 90), 2)
        events.append((e, f"Event {e}", rnd.randint(1, n_org), rnd.randint(1, n_ven),
                       rnd.randint(1, len(CATEGORIES)),
                       (start + timedelta(days=rnd.randint(0, 180))).strftime("%Y-%m-%d"), price))
        for name, mult, quota in TICKETS:
            tickets.append((len(tickets) + 1, e, name, round(price * mult, 2), quota))
    db.executemany("INSERT INTO event VALUES (?,?,?,?,?,?,?)", events)
    db.executemany("INSERT INTO ticket_type VALUES (?,?,?,?,?)", tickets)

    bookings, payments = [], []
    for b in range(1, n_book + 1):
        t = rnd.choice(tickets)                       # (id, event_id, name, price, quota)
        qty = rnd.randint(1, 4)
        when = datetime(2026, 9, 1) + timedelta(minutes=rnd.randint(0, 60 * 24 * 90))
        status = rnd.choices(["confirmed", "pending", "cancelled"], [80, 10, 10])[0]
        bookings.append((b, rnd.randint(1, n_cust), t[1], t[0], qty,
                         when.strftime("%Y-%m-%d %H:%M:%S"), status))
        if status != "pending":                       # pending bookings have no payment yet
            pay_status = "refunded" if status == "cancelled" else rnd.choices(["paid", "failed"], [95, 5])[0]
            payments.append((len(payments) + 1, b, round(t[3] * qty, 2), rnd.choice(METHODS),
                             (when + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"), pay_status))
    db.executemany("INSERT INTO booking VALUES (?,?,?,?,?,?,?)", bookings)
    db.executemany("INSERT INTO payment VALUES (?,?,?,?,?,?)", payments)
    db.commit()
    counts = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["organiser", "venue", "category", "customer", "event",
                        "ticket_type", "booking", "payment"]}
    db.close()
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "source.db"))
    ap.add_argument("--scale", type=float, default=1.0, help="dataset size multiplier")
    a = ap.parse_args()
    for table, n in build(Path(a.out), a.scale).items():
        print(f"{table:<12} {n:>7} rows")
    print(f"Created {a.out}")
