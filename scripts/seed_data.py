#!/usr/bin/env python
"""Build the AtlasTrip dataset.

Reads the hand-authored files in ``data/seed`` and turns them into the two
stores the network runs on:

* Postgres, for the relational inventory, the people and the budget ledger;
* TinyDB, for the policy clauses, entry rules and customer sites.

Flight fares and hotel rates are synthesised rather than listed by hand, but
the generator is seeded, so two runs on the same input produce byte-identical
output and the demo is reproducible.

Usage:  packages/atlastrip_core/.venv/bin/python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import json
import random

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg

from atlastrip_core import documents
from atlastrip_core.config import REPO_ROOT, settings


SEED_DIR = REPO_ROOT / "data" / "seed"
SCHEMA = REPO_ROOT / "packages" / "atlastrip_core" / "src" / "atlastrip_core" / "schema.sql"

RANDOM_SEED = 20261014

# Rate windows. Wide enough that any date in the shipped scenarios resolves.
HOTEL_WINDOW = (date(2026, 9, 1), date(2026, 12, 15))

# Modelled kilograms of CO2 equivalent per passenger kilometre, by cabin.
CO2_PER_KM = {"economy": 0.090, "premium_economy": 0.144, "business": 0.261, "first": 0.410}

# Each cabin is sold as one or more fare products.
# (product name, multiplier applied to the cabin's list fare, refundable)
FARE_PRODUCTS = {
    "economy": [("SAVER", 1.00, False), ("FLEX", 1.42, True)],
    "premium_economy": [("SAVER", 1.00, False), ("FLEX", 1.33, True)],
    "business": [("FLEX", 1.00, True)],
}

# (room type, multiplier on the hotel's base rate, refundable, breakfast)
ROOM_TYPES = [
    ("saver", 0.86, False, False),
    ("standard", 1.00, True, False),
    ("executive", 1.28, True, True),
]


def load(name: str) -> list[dict]:
    return json.loads((SEED_DIR / f"{name}.json").read_text())


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def jitter(rng: random.Random, spread: float) -> float:
    """A small multiplicative wobble, so prices are not suspiciously uniform."""
    return 1.0 + rng.uniform(-spread, spread)


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------


def build_flights(routes: list[dict], timezones: dict[str, str]) -> list[tuple]:
    """Expand route definitions into one row per (service, date, fare product)."""
    rows: list[tuple] = []
    rng = random.Random(RANDOM_SEED)

    for route in routes:
        window_start = date.fromisoformat(route["window"][0])
        window_end = date.fromisoformat(route["window"][1])
        legs = (
            (route["origin"], route["dest"], route["services"]),
            (route["dest"], route["origin"], route["returns"]),
        )

        for origin, dest, services in legs:
            departure_zone = ZoneInfo(timezones[origin])
            for service in services:
                hour, minute = (int(part) for part in service["depart_local"].split(":"))
                for day in daterange(window_start, window_end):
                    depart_local = datetime.combine(
                        day, time(hour, minute), tzinfo=departure_zone
                    )
                    depart_utc = depart_local.astimezone(ZoneInfo("UTC"))
                    arrive_utc = depart_utc + timedelta(
                        minutes=route["duration_minutes"]
                    )
                    # Fares peak mid-week when business demand is highest.
                    weekday_factor = 1.08 if day.weekday() in (0, 1, 2, 3) else 0.96

                    for cabin, list_fare in service["cabins"].items():
                        co2 = round(route["distance_km"] * CO2_PER_KM[cabin], 1)
                        for product, multiplier, refundable in FARE_PRODUCTS[cabin]:
                            base = round(
                                list_fare
                                * multiplier
                                * weekday_factor
                                * jitter(rng, 0.06),
                                2,
                            )
                            rows.append(
                                (
                                    service["carrier"],
                                    service["flight_no"],
                                    origin,
                                    dest,
                                    depart_utc,
                                    arrive_utc,
                                    route["duration_minutes"],
                                    service.get("stops", 0),
                                    cabin,
                                    f"{service['carrier']}-{cabin.upper()[:3]}-{product}",
                                    base,
                                    round(base * 0.11 + 68.0, 2),
                                    refundable,
                                    rng.randint(2, 34),
                                    co2,
                                    service["aircraft"],
                                )
                            )
    return rows


def build_hotel_rates(hotel_ids: dict[str, int], hotels: list[dict]) -> list[tuple]:
    """One rate row per hotel, night and room type."""
    rows: list[tuple] = []
    rng = random.Random(RANDOM_SEED + 1)
    start, end = HOTEL_WINDOW

    for hotel in hotels:
        hotel_id = hotel_ids[hotel["name"]]
        has_breakfast = "breakfast" in hotel["amenities"]
        for night in daterange(start, end):
            # Business hotels discount at the weekend.
            weekend_factor = 0.88 if night.weekday() in (4, 5) else 1.0
            for room_type, multiplier, refundable, executive_breakfast in ROOM_TYPES:
                rate = round(
                    hotel["base_rate"]
                    * multiplier
                    * weekend_factor
                    * jitter(rng, 0.04),
                    2,
                )
                rows.append(
                    (
                        hotel_id,
                        night,
                        room_type,
                        rate,
                        refundable,
                        has_breakfast or executive_breakfast,
                        rng.randint(0, 12),
                    )
                )
    return rows


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------


async def seed_postgres() -> dict[str, int]:
    counts: dict[str, int] = {}
    conn = await asyncpg.connect(dsn=settings().postgres_dsn)
    try:
        await conn.execute(SCHEMA.read_text())

        airports = load("airports")
        await conn.executemany(
            "INSERT INTO airports (iata, name, city, country, timezone)"
            " VALUES ($1, $2, $3, $4, $5)",
            [
                (a["iata"], a["name"], a["city"], a["country"], a["timezone"])
                for a in airports
            ],
        )
        counts["airports"] = len(airports)
        timezones = {a["iata"]: a["timezone"] for a in airports}

        cost_centers = load("cost_centers")
        await conn.executemany(
            "INSERT INTO cost_centers"
            " (id, name, owner_email, fiscal_quarter, quarterly_budget_usd)"
            " VALUES ($1, $2, $3, $4, $5)",
            [
                (
                    c["id"],
                    c["name"],
                    c["owner_email"],
                    c["fiscal_quarter"],
                    c["quarterly_budget_usd"],
                )
                for c in cost_centers
            ],
        )
        counts["cost_centers"] = len(cost_centers)

        employees = load("employees")
        await conn.executemany(
            "INSERT INTO employees (full_name, email, title, grade, home_city,"
            " home_iata, passport_country, cost_center_id, manager_email)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            [
                (
                    e["full_name"],
                    e["email"],
                    e["title"],
                    e["grade"],
                    e["home_city"],
                    e["home_iata"],
                    e["passport_country"],
                    e["cost_center_id"],
                    e["manager_email"],
                )
                for e in employees
            ],
        )
        counts["employees"] = len(employees)

        flights = build_flights(load("routes"), timezones)
        await conn.executemany(
            "INSERT INTO flights (carrier, flight_no, origin_iata, dest_iata,"
            " depart_utc, arrive_utc, duration_minutes, stops, cabin, fare_basis,"
            " base_fare_usd, taxes_usd, refundable, seats_available, co2_kg, aircraft)"
            " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)",
            flights,
        )
        counts["flights"] = len(flights)

        hotels = load("hotels")
        hotel_ids: dict[str, int] = {}
        for hotel in hotels:
            hotel_id = await conn.fetchval(
                "INSERT INTO hotels (name, city, country, address, latitude,"
                " longitude, star_rating, corporate_code, amenities)"
                " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id",
                hotel["name"],
                hotel["city"],
                hotel["country"],
                hotel["address"],
                hotel["latitude"],
                hotel["longitude"],
                hotel["star_rating"],
                hotel["corporate_code"],
                hotel["amenities"],
            )
            hotel_ids[hotel["name"]] = hotel_id
        counts["hotels"] = len(hotels)

        rates = build_hotel_rates(hotel_ids, hotels)
        await conn.executemany(
            "INSERT INTO hotel_rates (hotel_id, stay_date, room_type,"
            " nightly_rate_usd, refundable, breakfast_included, rooms_available)"
            " VALUES ($1,$2,$3,$4,$5,$6,$7)",
            rates,
        )
        counts["hotel_rates"] = len(rates)

        ground = load("ground_transport")
        await conn.executemany(
            "INSERT INTO ground_transport (city, mode, provider, description,"
            " price_usd, duration_minutes) VALUES ($1,$2,$3,$4,$5,$6)",
            [
                (
                    g["city"],
                    g["mode"],
                    g["provider"],
                    g["description"],
                    g["price_usd"],
                    g["duration_minutes"],
                )
                for g in ground
            ],
        )
        counts["ground_transport"] = len(ground)

        ledger = load("budget_ledger")
        await conn.executemany(
            "INSERT INTO budget_ledger (cost_center_id, trip_ref, description,"
            " amount_usd, kind) VALUES ($1,$2,$3,$4,$5)",
            [
                (
                    entry["cost_center_id"],
                    entry["trip_ref"],
                    entry["description"],
                    entry["amount_usd"],
                    entry["kind"],
                )
                for entry in ledger
            ],
        )
        counts["budget_ledger"] = len(ledger)
    finally:
        await conn.close()
    return counts


def seed_tinydb() -> dict[str, int]:
    documents.reset_all()
    counts = {}
    for collection, name in (
        (documents.POLICIES, "policies"),
        (documents.VISA_RULES, "visa_rules"),
        (documents.VENUES, "venues"),
    ):
        records = load(name)
        documents.replace_all(collection, records)
        counts[name] = len(records)
    return counts


async def main() -> None:
    print(f"Postgres : {settings().postgres_dsn}")
    print(f"TinyDB   : {settings().tinydb_dir}")
    print()

    postgres_counts = await seed_postgres()
    tinydb_counts = seed_tinydb()

    print("Postgres tables")
    for table, count in postgres_counts.items():
        print(f"  {table:<18} {count:>6,}")
    print("TinyDB collections")
    for collection, count in tinydb_counts.items():
        print(f"  {collection:<18} {count:>6,}")
    print("\nDataset ready.")


if __name__ == "__main__":
    asyncio.run(main())
