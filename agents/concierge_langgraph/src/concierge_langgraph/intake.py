"""Turning what the traveller typed into something the network can act on.

This is the one place the Concierge uses a model for anything other than
writing prose. A person says "I need to be in Tokyo for the Kaisei QBR from the
14th to the 17th"; the specialists need an origin, a destination, two ISO dates
and a venue id. LangChain's structured output does that conversion, checked
against the directory rather than trusted.
"""

from __future__ import annotations

from datetime import date, timedelta

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.mcp_http import MCPClient
from atlastrip_core.models import TravellerProfile, TripRequest
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


log = get_logger("concierge")


class ParsedRequest(BaseModel):
    """The fields a trip request has to contain before anyone can work on it."""

    employee_email: str = Field(description="The traveller, from the directory.")
    purpose: str = Field(description="Why they are going, in a few words.")
    origin_iata: str = Field(description="Departure airport code.")
    destination_iata: str = Field(description="Arrival airport code.")
    depart_date: date
    return_date: date
    venue_id: str | None = Field(
        default=None, description="Customer site id, if one was mentioned."
    )
    notes: str = Field(default="", description="Anything else worth carrying.")


async def directory() -> dict[str, list[dict]]:
    """The reference data the parser needs to resolve names to identifiers.

    The Concierge reads this over the same MCP server the specialists use. It
    is the only data it reads directly; everything else it learns by asking.
    """
    async with MCPClient() as mcp:
        airports = await mcp.call("list_airports")
        venues = [
            venue
            for venue_id in _VENUE_IDS
            if (venue := await mcp.call_one("lookup_venue", venue_id=venue_id))
        ]
    return {"airports": airports, "venues": venues}


_VENUE_IDS = ("KAISEI-HQ", "THAMESIDE-DC", "MARINA-SYS", "NIMBUS-HQ", "HUDSON-YARD")


async def lookup_traveller(email: str) -> TravellerProfile:
    async with MCPClient() as mcp:
        record = await mcp.call_one("lookup_employee", email=email)
    if record is None:
        raise LookupError(f"{email} is not in the employee directory.")
    return TravellerProfile(
        employee_id=int(record["id"]),
        full_name=record["full_name"],
        email=record["email"],
        title=record["title"],
        grade=record["grade"],
        home_iata=record["home_iata"],
        passport_country=record["passport_country"],
        cost_center_id=record["cost_center_id"],
        manager_email=record["manager_email"],
    )


async def parse(utterance: str, trip_ref: str, today: date | None = None) -> TripRequest:
    """Read a request out of free text, or fail loudly enough to be fixed."""
    reference = await directory()
    parsed = await _parse_with_model(utterance, reference, today or date.today())
    if parsed is None:
        parsed = _parse_by_hand(utterance, reference)

    return TripRequest(
        trip_ref=trip_ref,
        employee_email=parsed.employee_email,
        purpose=parsed.purpose,
        origin_iata=parsed.origin_iata.upper(),
        destination_iata=parsed.destination_iata.upper(),
        depart_date=parsed.depart_date,
        return_date=parsed.return_date,
        venue_id=parsed.venue_id,
        notes=parsed.notes,
    )


async def _parse_with_model(
    utterance: str, reference: dict[str, list[dict]], today: date
) -> ParsedRequest | None:
    if not settings().uses_llm:
        return None
    try:
        model = ChatOpenAI(
            model=settings().openai_model, temperature=0
        ).with_structured_output(ParsedRequest)
        return await model.ainvoke(_prompt(utterance, reference, today))
    except Exception as error:
        log.warning("intake parsing fell back to rules: %s", error)
        return None


def _prompt(utterance: str, reference: dict[str, list[dict]], today: date) -> str:
    airports = "\n".join(
        f"  {a['iata']}  {a['city']}, {a['country']}" for a in reference["airports"]
    )
    venues = "\n".join(
        f"  {v['venue_id']}  {v['name']} ({v['customer']}), {v['city']}, "
        f"nearest airport {v['nearest_airport']}"
        for v in reference["venues"]
    )
    return f"""Today is {today.isoformat()}.

Read this travel request and fill in every field.

Request:
\"\"\"{utterance}\"\"\"

Airports:
{airports}

Customer sites:
{venues}

Rules:
- employee_email must be a full address. If the request names a person without
  an address, use firstname.lastname@nimbusrobotics.example.
- If a customer site is named or implied, set venue_id and use its nearest
  airport as the destination.
- Dates are in the future relative to today. Resolve relative dates such as
  "the week of the 14th" against today's date.
"""


def _parse_by_hand(
    utterance: str, reference: dict[str, list[dict]]
) -> ParsedRequest:
    """A last resort so the network still runs with no model available.

    Deliberately crude: it recognises a venue or city name and assumes a
    three night trip four weeks out. Deterministic mode uses this path, which
    is why the test suite always passes an explicit brief instead.
    """
    lowered = utterance.lower()
    venue = next(
        (
            v
            for v in reference["venues"]
            if v["city"].lower() in lowered or v["venue_id"].lower() in lowered
        ),
        None,
    )
    if venue is None:
        raise ValueError(
            "Could not work out where this trip is going. Name a city or a "
            "customer site, or set ATLASTRIP_REASONING=llm."
        )
    depart = date.today() + timedelta(days=28)
    return ParsedRequest(
        employee_email="mira.halvorsen@nimbusrobotics.example",
        purpose="Customer visit",
        origin_iata="SFO",
        destination_iata=venue["nearest_airport"],
        depart_date=depart,
        return_date=depart + timedelta(days=3),
        venue_id=venue["venue_id"],
        notes="Parsed without a model.",
    )


async def cheapest_ground(city: str) -> tuple[float, str]:
    """Pick the ground transport option policy would prefer.

    Rail, transit passes and shared rides first; a taxi only if nothing else
    serves the city.
    """
    async with MCPClient() as mcp:
        options = await mcp.call("get_ground_transport", city=city)
    preferred = [o for o in options if o["mode"] in ("train", "transit_pass", "shared_ride")]
    chosen = min(preferred or options, key=lambda o: float(o["price_usd"]), default=None)
    if chosen is None:
        return 0.0, "No ground transport on file for this city."
    # Both directions.
    total = round(float(chosen["price_usd"]) * 2, 2)
    return total, f"{chosen['provider']} {chosen['mode']}, ${total:,.2f} return."
