-- AtlasTrip operational schema.
--
-- Everything relational lives here: who travels, what is bookable, what it
-- costs and what has been committed against a budget. The A2A task store adds
-- its own `a2a_tasks` table at runtime; it is not declared here because the
-- SDK owns that schema.

DROP TABLE IF EXISTS budget_ledger CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS hotel_rates CASCADE;
DROP TABLE IF EXISTS hotels CASCADE;
DROP TABLE IF EXISTS flights CASCADE;
DROP TABLE IF EXISTS ground_transport CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS cost_centers CASCADE;
DROP TABLE IF EXISTS airports CASCADE;

CREATE TABLE airports (
    iata        CHAR(3) PRIMARY KEY,
    name        TEXT        NOT NULL,
    city        TEXT        NOT NULL,
    country     TEXT        NOT NULL,
    timezone    TEXT        NOT NULL
);

CREATE TABLE cost_centers (
    id                   TEXT PRIMARY KEY,
    name                 TEXT           NOT NULL,
    owner_email          TEXT           NOT NULL,
    fiscal_quarter       TEXT           NOT NULL,
    quarterly_budget_usd NUMERIC(12, 2) NOT NULL
);

CREATE TABLE employees (
    id               SERIAL PRIMARY KEY,
    full_name        TEXT    NOT NULL,
    email            TEXT    NOT NULL UNIQUE,
    title            TEXT    NOT NULL,
    -- Grade drives cabin entitlement and approval thresholds in travel policy.
    grade            TEXT    NOT NULL,
    home_city        TEXT    NOT NULL,
    home_iata        CHAR(3) NOT NULL REFERENCES airports (iata),
    passport_country TEXT    NOT NULL,
    cost_center_id   TEXT    NOT NULL REFERENCES cost_centers (id),
    manager_email    TEXT    NOT NULL
);

CREATE TABLE flights (
    id              SERIAL PRIMARY KEY,
    carrier         TEXT           NOT NULL,
    flight_no       TEXT           NOT NULL,
    origin_iata     CHAR(3)        NOT NULL REFERENCES airports (iata),
    dest_iata       CHAR(3)        NOT NULL REFERENCES airports (iata),
    depart_utc      TIMESTAMPTZ    NOT NULL,
    arrive_utc      TIMESTAMPTZ    NOT NULL,
    duration_minutes INTEGER       NOT NULL,
    stops           INTEGER        NOT NULL DEFAULT 0,
    cabin           TEXT           NOT NULL,
    fare_basis      TEXT           NOT NULL,
    base_fare_usd   NUMERIC(10, 2) NOT NULL,
    taxes_usd       NUMERIC(10, 2) NOT NULL,
    refundable      BOOLEAN        NOT NULL,
    seats_available INTEGER        NOT NULL,
    co2_kg          NUMERIC(8, 1)  NOT NULL,
    aircraft        TEXT           NOT NULL
);

CREATE INDEX flights_route_idx
    ON flights (origin_iata, dest_iata, depart_utc);

CREATE TABLE hotels (
    id                     SERIAL PRIMARY KEY,
    name                   TEXT          NOT NULL,
    city                   TEXT          NOT NULL,
    country                TEXT          NOT NULL,
    address                TEXT          NOT NULL,
    latitude               NUMERIC(9, 6) NOT NULL,
    longitude              NUMERIC(9, 6) NOT NULL,
    star_rating            INTEGER       NOT NULL,
    corporate_code         TEXT,
    amenities              TEXT[]        NOT NULL DEFAULT '{}'
);

CREATE INDEX hotels_city_idx ON hotels (city);

CREATE TABLE hotel_rates (
    id                 SERIAL PRIMARY KEY,
    hotel_id           INTEGER        NOT NULL REFERENCES hotels (id) ON DELETE CASCADE,
    stay_date          DATE           NOT NULL,
    room_type          TEXT           NOT NULL,
    nightly_rate_usd   NUMERIC(10, 2) NOT NULL,
    refundable         BOOLEAN        NOT NULL,
    breakfast_included BOOLEAN        NOT NULL,
    rooms_available    INTEGER        NOT NULL,
    UNIQUE (hotel_id, stay_date, room_type)
);

CREATE INDEX hotel_rates_date_idx ON hotel_rates (stay_date);

CREATE TABLE ground_transport (
    id               SERIAL PRIMARY KEY,
    city             TEXT           NOT NULL,
    mode             TEXT           NOT NULL,
    provider         TEXT           NOT NULL,
    description      TEXT           NOT NULL,
    price_usd        NUMERIC(10, 2) NOT NULL,
    duration_minutes INTEGER        NOT NULL
);

-- Money already committed against a cost centre. Ledger reads the running
-- total before it authorises anything and writes a commitment when it does.
CREATE TABLE budget_ledger (
    id             SERIAL PRIMARY KEY,
    cost_center_id TEXT           NOT NULL REFERENCES cost_centers (id),
    trip_ref       TEXT           NOT NULL,
    description    TEXT           NOT NULL,
    amount_usd     NUMERIC(12, 2) NOT NULL,
    kind           TEXT           NOT NULL CHECK (kind IN ('commitment', 'actual')),
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE INDEX budget_ledger_cc_idx ON budget_ledger (cost_center_id);

CREATE TABLE bookings (
    id         SERIAL PRIMARY KEY,
    trip_ref   TEXT        NOT NULL,
    kind       TEXT        NOT NULL,
    reference  TEXT        NOT NULL,
    payload    JSONB       NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
