"""Hearth's lodging logic, with no framework and no model in sight.

Hearth's brief is to find somewhere good to stay near where the traveller has
to be. It weighs proximity, price and quality against each other and makes a
call. It is deliberately *not* a policy engine: the nightly cap arrives as
guidance, and Hearth is allowed to decide that a room a few dollars over the
cap and two hundred metres from the customer's front door is the better
option. Sentinel is the agent that gets to overrule that, and when it does the
Concierge comes back and asks again with the cap as a hard constraint.

That negotiation is the interesting part of the demo, and it only exists
because judgement and enforcement live in different agents.
"""

from __future__ import annotations

from typing import Any

from atlastrip_core.mcp_http import MCPClient
from atlastrip_core.models import HotelOffer, StayBrief, StayProposal

# How Hearth trades off the three things it cares about.
#
# The units are chosen so the weights mean something. Price is scored as the
# premium over the cheapest room in the shortlist, so 0.5 means "half again as
# expensive". Distance is scored in kilometres from the nearest option. Quality
# is scored in stars above the worst option.
#
# Deliberately not min-max normalisation on all three: that would make the
# score scale-invariant, and a scale-invariant ranking will happily pay $900 a
# night to save four hundred metres, because it only ever sees "most expensive"
# and "nearest" rather than how much more and how much nearer.
WEIGHT_PRICE = 0.60
"""Cost of being twice as expensive as the cheapest room."""
WEIGHT_DISTANCE = 1.20
"""Cost of each kilometre further from the venue than the nearest room."""
WEIGHT_QUALITY = 0.35
"""Credit for each star above the worst room in the shortlist."""

REQUIRED_AMENITIES = ("wifi", "desk")
SHORTLIST_SIZE = 6


async def shortlist(brief: StayBrief) -> list[dict[str, Any]]:
    """Pull candidate hotels from the inventory over MCP."""
    async with MCPClient() as mcp:
        rows = await mcp.call(
            "search_hotels",
            city=brief.city,
            check_in=brief.check_in.isoformat(),
            check_out=brief.check_out.isoformat(),
            venue_id=brief.venue_id,
            # Only a re-ask turns the cap into a filter.
            max_nightly_rate=brief.nightly_cap_usd if brief.enforce_cap else None,
            min_star_rating=brief.min_star_rating,
            limit=20,
        )

    usable = [row for row in rows if _has_required_amenities(row)]
    if brief.max_distance_km is not None:
        usable = [
            row
            for row in usable
            if (row.get("distance_km_to_venue") or 0) <= brief.max_distance_km
        ]
    return rank(usable)[:SHORTLIST_SIZE]


def _has_required_amenities(row: dict[str, Any]) -> bool:
    amenities = set(row.get("amenities") or [])
    return all(required in amenities for required in REQUIRED_AMENITIES)


def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order candidates best-first, lowest score winning.

    Every option is scored against the best option in the shortlist on each
    dimension, in that dimension's own units, so the trade-off stays honest as
    the numbers get large.
    """
    if len(rows) <= 1:
        return list(rows)

    cheapest = min(float(row["nightly_rate_usd"]) for row in rows) or 1.0
    nearest = min(float(row.get("distance_km_to_venue") or 0.0) for row in rows)
    worst_stars = min(int(row["star_rating"]) for row in rows)

    def score(row: dict[str, Any]) -> float:
        premium = float(row["nightly_rate_usd"]) / cheapest - 1.0
        extra_km = float(row.get("distance_km_to_venue") or 0.0) - nearest
        extra_stars = int(row["star_rating"]) - worst_stars
        return (
            WEIGHT_PRICE * premium
            + WEIGHT_DISTANCE * extra_km
            - WEIGHT_QUALITY * extra_stars
        )

    return sorted(rows, key=score)


def to_offer(row: dict[str, Any], nights: int) -> HotelOffer:
    nightly = round(float(row["nightly_rate_usd"]), 2)
    return HotelOffer(
        offer_id=f"HT-{row['hotel_id']}",
        hotel_id=int(row["hotel_id"]),
        name=row["name"],
        city=row["city"],
        address=row["address"],
        star_rating=int(row["star_rating"]),
        distance_km_to_venue=float(row.get("distance_km_to_venue") or 0.0),
        nightly_rate_usd=nightly,
        nights=nights,
        total_usd=round(nightly * nights, 2),
        refundable=bool(row["refundable"]),
        breakfast_included=bool(row["breakfast_included"]),
        corporate_code=row.get("corporate_code"),
        amenities=list(row.get("amenities") or []),
    )


def assemble(
    brief: StayBrief,
    candidates: list[dict[str, Any]],
    *,
    offer_id: str | None = None,
    rationale: str = "",
) -> StayProposal:
    """Turn the shortlist plus an optional choice into the proposal we return.

    An ``offer_id`` the crew invented, rather than chose, is ignored: the top
    of the ranking is used instead so we never quote a room that is not on the
    shortlist.
    """
    if not candidates:
        raise LookupError(
            f"No hotel in {brief.city} matches the brief for "
            f"{brief.check_in} to {brief.check_out}."
        )

    nights = max((brief.check_out - brief.check_in).days, 1)
    chosen = _pick(candidates, offer_id)
    recommended = to_offer(chosen, nights)
    alternatives = [
        to_offer(row, nights)
        for row in candidates
        if row["hotel_id"] != chosen["hotel_id"]
    ][:3]

    return StayProposal(
        trip_ref=brief.trip_ref,
        recommended=recommended,
        alternatives=alternatives,
        total_usd=recommended.total_usd,
        rationale=rationale or _default_rationale(recommended, brief),
    )


def _pick(rows: list[dict[str, Any]], offer_id: str | None) -> dict[str, Any]:
    if offer_id:
        wanted = offer_id.removeprefix("HT-")
        for row in rows:
            if str(row["hotel_id"]) == wanted:
                return row
    return rows[0]


def _default_rationale(offer: HotelOffer, brief: StayBrief) -> str:
    proximity = (
        f"{offer.distance_km_to_venue:.1f} km from the meeting venue"
        if brief.venue_id
        else f"in central {offer.city}"
    )
    rate = (
        f"${offer.nightly_rate_usd:,.2f} a night"
        if not offer.corporate_code
        else f"${offer.nightly_rate_usd:,.2f} a night on the {offer.corporate_code} rate"
    )
    return (
        f"{offer.name}, {offer.star_rating} star, {proximity}, {rate} "
        f"for {offer.nights} nights."
    )


async def source_stay(brief: StayBrief) -> StayProposal:
    """The whole job, without a model. Used in deterministic mode and in tests."""
    return assemble(brief, await shortlist(brief))
