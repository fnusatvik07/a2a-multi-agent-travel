"""Skyline's flight logic, with no framework and no model in sight.

Everything here is deterministic and testable: it pulls candidates from the
inventory over MCP, scores them, and assembles a proposal. The Google ADK agent
in ``agent.py`` sits on top and makes the judgement call about which candidate
to take; if it is unavailable or answers with something unusable, the ranking
below is what ships.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from atlastrip_core.mcp_http import MCPClient
from atlastrip_core.models import FlightBrief, FlightOffer, FlightProposal


LONG_HAUL_MINUTES = 480
"""Eight hours. Past this, a wider seat starts to be worth paying for."""

PREMIUM_PREMIUM_LIMIT = 1.8
"""How much more than the economy fare Skyline will pay for premium economy on
a long haul before it stops being defensible as value."""

SHORTLIST_SIZE = 6


async def shortlist(brief: FlightBrief) -> dict[str, list[dict[str, Any]]]:
    """Pull the candidate flights for both directions from the MCP server."""
    async with MCPClient() as mcp:
        outbound = await mcp.call(
            "search_flights",
            origin_iata=brief.origin_iata,
            dest_iata=brief.dest_iata,
            depart_date=brief.depart_date.isoformat(),
            cabin=brief.cabin,
            max_stops=brief.max_stops,
            preferred_carriers=brief.preferred_carriers or None,
            limit=24,
        )
        inbound = await mcp.call(
            "search_flights",
            origin_iata=brief.dest_iata,
            dest_iata=brief.origin_iata,
            depart_date=brief.return_date.isoformat(),
            cabin=brief.cabin,
            max_stops=brief.max_stops,
            preferred_carriers=brief.preferred_carriers or None,
            limit=24,
        )
    return {
        "outbound": _trim(outbound, brief),
        "inbound": _trim(inbound, brief),
    }


def _trim(rows: list[dict[str, Any]], brief: FlightBrief) -> list[dict[str, Any]]:
    """Cut the raw inventory down to a shortlist worth showing anyone.

    The cabin is chosen here rather than dictated by the caller: on a long
    haul, premium economy is offered when it is within a defensible multiple of
    the cheapest economy fare. Whether the traveller is *entitled* to that cabin
    is not Skyline's call, and Sentinel will say so.
    """
    if not rows:
        return []
    if brief.cabin:
        chosen_cabin = brief.cabin
    else:
        long_haul = rows[0]["duration_minutes"] >= LONG_HAUL_MINUTES
        cheapest = {cabin: None for cabin in ("economy", "premium_economy")}
        for row in rows:
            cabin = row["cabin"]
            if cabin in cheapest and (
                cheapest[cabin] is None or row["total_usd"] < cheapest[cabin]
            ):
                cheapest[cabin] = row["total_usd"]
        chosen_cabin = "economy"
        if (
            long_haul
            and cheapest["economy"]
            and cheapest["premium_economy"]
            and cheapest["premium_economy"]
            <= cheapest["economy"] * PREMIUM_PREMIUM_LIMIT
        ):
            chosen_cabin = "premium_economy"

    candidates = [row for row in rows if row["cabin"] == chosen_cabin] or rows
    candidates.sort(key=_score)
    return candidates[:SHORTLIST_SIZE]


def _score(row: dict[str, Any]) -> tuple[float, int, int]:
    """Cheapest first, then fewest stops, then shortest.

    Returned as a tuple so the ordering is obvious at a glance and stable
    across runs.
    """
    return (row["total_usd"], row["stops"], row["duration_minutes"])


def to_offer(row: dict[str, Any], direction: str) -> FlightOffer:
    return FlightOffer(
        offer_id=f"FL-{row['id']}",
        direction=direction,
        carrier=row["carrier"],
        flight_no=row["flight_no"],
        origin_iata=row["origin_iata"],
        dest_iata=row["dest_iata"],
        depart_utc=datetime.fromisoformat(row["depart_utc"]),
        arrive_utc=datetime.fromisoformat(row["arrive_utc"]),
        duration_minutes=row["duration_minutes"],
        stops=row["stops"],
        cabin=row["cabin"],
        fare_basis=row["fare_basis"],
        total_usd=round(float(row["total_usd"]), 2),
        refundable=row["refundable"],
        co2_kg=float(row["co2_kg"]),
        aircraft=row["aircraft"],
    )


def assemble(
    brief: FlightBrief,
    candidates: dict[str, list[dict[str, Any]]],
    *,
    outbound_offer_id: str | None = None,
    inbound_offer_id: str | None = None,
    rationale: str = "",
) -> FlightProposal:
    """Turn a shortlist plus an optional choice into the proposal we return.

    ``outbound_offer_id`` and ``inbound_offer_id`` come from the ADK agent when
    it has picked. Anything unrecognised is ignored and the top of the ranking
    is used instead, so a confused model can never produce an unbookable
    itinerary.
    """
    outbound_rows = candidates["outbound"]
    inbound_rows = candidates["inbound"]
    if not outbound_rows or not inbound_rows:
        raise LookupError(
            f"No flights available for {brief.origin_iata}-{brief.dest_iata} "
            f"on {brief.depart_date} / {brief.return_date}."
        )

    outbound = _pick(outbound_rows, outbound_offer_id)
    inbound = _pick(inbound_rows, inbound_offer_id)

    chosen = {outbound["id"], inbound["id"]}
    alternatives = [
        to_offer(row, direction)
        for direction, rows in (("outbound", outbound_rows), ("return", inbound_rows))
        for row in rows
        if row["id"] not in chosen
    ][:4]

    outbound_offer = to_offer(outbound, "outbound")
    inbound_offer = to_offer(inbound, "return")
    return FlightProposal(
        trip_ref=brief.trip_ref,
        outbound=outbound_offer,
        inbound=inbound_offer,
        total_usd=round(outbound_offer.total_usd + inbound_offer.total_usd, 2),
        alternatives=alternatives,
        rationale=rationale or _default_rationale(outbound_offer, inbound_offer),
    )


def _pick(rows: list[dict[str, Any]], offer_id: str | None) -> dict[str, Any]:
    if offer_id:
        wanted = offer_id.removeprefix("FL-")
        for row in rows:
            if str(row["id"]) == wanted:
                return row
    return rows[0]


def _default_rationale(outbound: FlightOffer, inbound: FlightOffer) -> str:
    stops = "non-stop" if outbound.stops == 0 and inbound.stops == 0 else "with a connection"
    return (
        f"{outbound.carrier} {stops} in {outbound.cabin.replace('_', ' ')}, "
        f"the cheapest fare on the requested dates at "
        f"${outbound.total_usd + inbound.total_usd:,.2f} round trip."
    )


async def source_flights(brief: FlightBrief) -> FlightProposal:
    """The whole job, without a model. Used in deterministic mode and in tests."""
    candidates = await shortlist(brief)
    return assemble(brief, candidates)
