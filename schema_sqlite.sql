-- SOURCE schema (SQLite). The "old system" that gets migrated.
-- SQLite is loosely typed: no CHECK rules, dates stored as TEXT, money as REAL.
PRAGMA foreign_keys = ON;

CREATE TABLE organiser (
    organiser_id INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE
);
CREATE TABLE venue (
    venue_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    suburb   TEXT NOT NULL,
    capacity INTEGER NOT NULL
);
CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);
CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE
);
CREATE TABLE event (
    event_id     INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    organiser_id INTEGER NOT NULL REFERENCES organiser(organiser_id),
    venue_id     INTEGER NOT NULL REFERENCES venue(venue_id),
    category_id  INTEGER NOT NULL REFERENCES category(category_id),
    event_date   TEXT NOT NULL,          -- 'YYYY-MM-DD'
    base_price   REAL NOT NULL
);
CREATE TABLE ticket_type (
    ticket_type_id INTEGER PRIMARY KEY,
    event_id       INTEGER NOT NULL REFERENCES event(event_id),
    name           TEXT NOT NULL,
    price          REAL NOT NULL,
    quota          INTEGER NOT NULL
);
CREATE TABLE booking (
    booking_id     INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customer(customer_id),
    event_id       INTEGER NOT NULL REFERENCES event(event_id),
    ticket_type_id INTEGER NOT NULL REFERENCES ticket_type(ticket_type_id),
    quantity       INTEGER NOT NULL,
    booking_date   TEXT NOT NULL,        -- 'YYYY-MM-DD HH:MM:SS'
    status         TEXT NOT NULL
);
CREATE TABLE payment (
    payment_id INTEGER PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES booking(booking_id),
    amount     REAL NOT NULL,
    method     TEXT NOT NULL,
    paid_at    TEXT NOT NULL,
    status     TEXT NOT NULL
);
