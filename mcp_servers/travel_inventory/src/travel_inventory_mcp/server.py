"""The travel inventory MCP server.

One Model Context Protocol server holds every tool that touches AtlasTrip's
data, and all four specialist agents connect to it over streamable HTTP. That
split is the whole architecture in one sentence:

    MCP gives an agent its tools. A2A lets agents give each other work.

Because the tools live here rather than inside any one agent, the Google ADK
agent, the CrewAI agent, the LlamaIndex agent and the Pydantic AI agent all
read the same inventory through the same interface, and swapping a framework
never means rewriting a tool.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from atlastrip_core import db, documents
from atlastrip_core.console import get_logger
from mcp.server import MCPServer

from .geo import haversine_km


log = get_logger("mcp")

server = MCPServer(
    name="atlastrip-travel-inventory",
    version="1.0.0",
    instructions=(
        "Read-only access to AtlasTrip's flight and lodging inventory, plus the "
        "employee directory and cost centre budgets. Dates are ISO-8601. All "
        "prices are US dollars."
    ),
)


def _iso(value: Any) -> Any:
    """Make Postgres values JSON-safe without losing precision that matters."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "quantize"):  # decimal.Decimal
        return float(value)
    return value


def _rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _iso(value) for key, value in record.items()} for record in records]


# --------------------------------------------------------------------------
# Air
# --------------------------------------------------------------------------


@server.tool(
    description=(
        "Search bookable flights on one city pair for one departure date. "
        "Returns the cheapest fare products first, with the total fare "
        "(base plus taxes), cabin, duration, stop count and modelled CO2."
    )
)
async def search_flights(
    origin_iata: str,
    dest_iata: str,
    depart_date: str,
    cabin: str | None = None,
    max_stops: int | None = None,
    preferred_carriers: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Args:
    origin_iata: Three letter departure airport code, e.g. ``SFO``.
    dest_iata: Three letter arrival airport code, e.g. ``HND``.
    depart_date: Departure date in the airport's local calendar, ``YYYY-MM-DD``.
    cabin: Restrict to ``economy``, ``premium_economy`` or ``business``.
    max_stops: Drop itineraries with more stops than this.
    preferred_carriers: Two letter carrier codes to restrict the search to.
    limit: Maximum rows to return.
    """
    rows = await db.fetch(
        """
        SELECT f.id, f.carrier, f.flight_no, f.origin_iata, f.dest_iata,
               f.depart_utc, f.arrive_utc, f.duration_minutes, f.stops, f.cabin,
               f.fare_basis, (f.base_fare_usd + f.taxes_usd) AS total_usd,
               f.base_fare_usd, f.taxes_usd, f.refundable, f.seats_available,
               f.co2_kg, f.aircraft
          FROM flights f
          JOIN airports a ON a.iata = f.origin_iata
         -- The caller means the departure date on the departure board, so the
         -- comparison has to happen in the origin airport's own timezone.
         WHERE f.origin_iata = $1
           AND f.dest_iata = $2
           AND (f.depart_utc AT TIME ZONE a.timezone)::date = $3::date
           AND f.seats_available > 0
           AND ($4::text IS NULL OR f.cabin = $4)
           AND ($5::int IS NULL OR f.stops <= $5)
           AND ($6::text[] IS NULL OR f.carrier = ANY($6))
         ORDER BY (f.base_fare_usd + f.taxes_usd) ASC
         LIMIT $7
        """,
        origin_iata.upper(),
        dest_iata.upper(),
        date.fromisoformat(depart_date),
        cabin,
        max_stops,
        [c.upper() for c in preferred_carriers] if preferred_carriers else None,
        limit,
    )
    log.info(
        "search_flights %s->%s on %s cabin=%s -> %d rows",
        origin_iata,
        dest_iata,
        depart_date,
        cabin or "any",
        len(rows),
    )
    return _rows(rows)


@server.tool(description="List the airports AtlasTrip has inventory for.")
async def list_airports() -> list[dict[str, Any]]:
    return _rows(await db.fetch("SELECT * FROM airports ORDER BY iata"))


# --------------------------------------------------------------------------
# Lodging
# --------------------------------------------------------------------------


@server.tool(
    description=(
        "Search hotels in a city for a date range. When a venue_id is given, "
        "each result carries its straight-line distance to that venue, which "
        "is the field to rank on when the traveller has meetings there."
    )
)
async def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    venue_id: str | None = None,
    max_nightly_rate: float | None = None,
    min_star_rating: int | None = None,
    room_type: str = "standard",
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Args:
    city: City name as it appears in the inventory, e.g. ``Tokyo``.
    check_in: First night, ``YYYY-MM-DD``.
    check_out: Departure morning, ``YYYY-MM-DD``. Not charged.
    venue_id: Customer site to measure distance from, e.g. ``KAISEI-HQ``.
    max_nightly_rate: Drop rooms above this nightly rate in US dollars.
    min_star_rating: Drop hotels below this star rating.
    room_type: ``saver`` (non-refundable), ``standard`` or ``executive``.
    limit: Maximum rows to return.
    """
    first_night = date.fromisoformat(check_in)
    last_night = date.fromisoformat(check_out) - timedelta(days=1)
    nights = max((last_night - first_night).days + 1, 1)

    rows = await db.fetch(
        """
        SELECT h.id AS hotel_id, h.name, h.city, h.country, h.address,
               h.latitude, h.longitude, h.star_rating, h.corporate_code,
               h.amenities,
               ROUND(AVG(r.nightly_rate_usd), 2) AS nightly_rate_usd,
               COUNT(r.id)                        AS nights_priced,
               BOOL_AND(r.refundable)             AS refundable,
               BOOL_AND(r.breakfast_included)     AS breakfast_included,
               MIN(r.rooms_available)             AS rooms_available
          FROM hotels h
          JOIN hotel_rates r ON r.hotel_id = h.id
         WHERE h.city = $1
           AND r.room_type = $2
           AND r.stay_date BETWEEN $3 AND $4
           AND ($5::int IS NULL OR h.star_rating >= $5)
      GROUP BY h.id
        HAVING MIN(r.rooms_available) > 0
           AND COUNT(r.id) = $6
           AND ($7::numeric IS NULL OR AVG(r.nightly_rate_usd) <= $7)
        """,
        city,
        room_type,
        first_night,
        last_night,
        min_star_rating,
        nights,
        max_nightly_rate,
    )

    venue = _venue(venue_id) if venue_id else None
    results = []
    for row in _rows(rows):
        nightly = float(row["nightly_rate_usd"])
        row["nights"] = nights
        row["total_usd"] = round(nightly * nights, 2)
        row["distance_km_to_venue"] = (
            haversine_km(
                float(row["latitude"]),
                float(row["longitude"]),
                venue["latitude"],
                venue["longitude"],
            )
            if venue
            else None
        )
        results.append(row)

    # Nearest first when we know where the traveller has to be, else cheapest.
    key = (
        (lambda r: (r["distance_km_to_venue"], r["total_usd"]))
        if venue
        else (lambda r: r["total_usd"])
    )
    results.sort(key=key)
    log.info(
        "search_hotels %s %s..%s venue=%s cap=%s -> %d rows",
        city,
        check_in,
        check_out,
        venue_id or "-",
        max_nightly_rate or "-",
        len(results),
    )
    return results[:limit]


@server.tool(
    description="Ground transport options between the airport and the city centre."
)
async def get_ground_transport(city: str) -> list[dict[str, Any]]:
    return _rows(
        await db.fetch(
            "SELECT city, mode, provider, description, price_usd, duration_minutes"
            "  FROM ground_transport WHERE city = $1 ORDER BY price_usd",
            city,
        )
    )


# --------------------------------------------------------------------------
# People, sites and money
# --------------------------------------------------------------------------


@server.tool(
    description=(
        "Look up an employee by email. Returns their grade, home airport, "
        "passport country, cost centre and manager, which the other agents "
        "need in order to apply policy and route approvals."
    )
)
async def lookup_employee(email: str) -> dict[str, Any] | None:
    row = await db.fetch_one("SELECT * FROM employees WHERE email = $1", email)
    return {key: _iso(value) for key, value in row.items()} if row else None


@server.tool(description="Look up a customer site by its venue id.")
async def lookup_venue(venue_id: str) -> dict[str, Any] | None:
    return _venue(venue_id)


@server.tool(
    description=(
        "Current budget position of a cost centre: the quarterly allowance, "
        "everything already committed or spent against it, and what is left."
    )
)
async def get_cost_center_budget(cost_center_id: str) -> dict[str, Any] | None:
    centre = await db.fetch_one(
        "SELECT * FROM cost_centers WHERE id = $1", cost_center_id
    )
    if centre is None:
        return None
    committed = await db.fetch_one(
        "SELECT COALESCE(SUM(amount_usd), 0) AS total"
        "  FROM budget_ledger WHERE cost_center_id = $1",
        cost_center_id,
    )
    budget = float(centre["quarterly_budget_usd"])
    spent = float(committed["total"]) if committed else 0.0
    return {
        "cost_center_id": centre["id"],
        "name": centre["name"],
        "owner_email": centre["owner_email"],
        "fiscal_quarter": centre["fiscal_quarter"],
        "quarterly_budget_usd": budget,
        "committed_usd": round(spent, 2),
        "remaining_usd": round(budget - spent, 2),
    }


@server.tool(
    description=(
        "Write a commitment against a cost centre. Call this only once a trip "
        "is authorised; it moves real money in the ledger."
    )
)
async def record_commitment(
    cost_center_id: str, trip_ref: str, description: str, amount_usd: float
) -> dict[str, Any]:
    await db.execute(
        "INSERT INTO budget_ledger (cost_center_id, trip_ref, description,"
        " amount_usd, kind) VALUES ($1, $2, $3, $4, 'commitment')",
        cost_center_id,
        trip_ref,
        description,
        amount_usd,
    )
    log.info("record_commitment %s %s $%.2f", cost_center_id, trip_ref, amount_usd)
    return {"recorded": True, "cost_center_id": cost_center_id, "trip_ref": trip_ref}


def _venue(venue_id: str) -> dict[str, Any] | None:
    matches = documents.find(documents.VENUES, venue_id=venue_id)
    return matches[0] if matches else None
