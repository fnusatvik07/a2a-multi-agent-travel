"""The last thing the Concierge does: say what happened, in English."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.models import Itinerary

log = get_logger("concierge")

SYSTEM = """\
You write the confirmation a travelling employee receives. Four specialist
agents produced the details below; you turn them into something readable.

Cover, in this order and in no more than one short paragraph plus a few lines:
  the flights and cabin, the hotel and what it costs, anything policy flagged,
  and what the traveller has to do next.

Read the trip status carefully before you write the closing line. The policy
findings describe what the trip needed; the budget decision says whether that
has since happened. When the status is confirmed, the approval has already
been granted and there is nothing left for the traveller to chase. Do not ask
them to obtain an approval they already have.

Be concrete about times, prices and names. Do not invent anything that is not
in the data. Do not use bullet symbols other than a plain hyphen.
"""


async def write(itinerary: Itinerary) -> str:
    """Ask the model for the summary, and fall back to a plain rendering."""
    if not settings().uses_llm:
        return plain(itinerary)
    try:
        model = ChatOpenAI(model=settings().openai_model, temperature=0.3)
        response = await model.ainvoke(
            [("system", SYSTEM), ("human", facts(itinerary))]
        )
        return str(response.content).strip()
    except Exception as error:
        log.warning("narrative fell back to the plain rendering: %s", error)
        return plain(itinerary)


def facts(itinerary: Itinerary) -> str:
    lines = [
        f"Trip {itinerary.trip_ref}, status {itinerary.status}.",
        f"Traveller: {itinerary.traveller.full_name}, "
        f"{itinerary.traveller.title}, grade {itinerary.traveller.grade}.",
        f"Purpose: {itinerary.request.purpose}.",
    ]
    if itinerary.flights:
        out, back = itinerary.flights.outbound, itinerary.flights.inbound
        lines += [
            f"Outbound: {out.carrier} {out.flight_no}, {out.origin_iata} to "
            f"{out.dest_iata}, departs {out.depart_utc:%Y-%m-%d %H:%M} UTC, "
            f"{out.cabin.replace('_', ' ')}, "
            f"{'refundable' if out.refundable else 'non-refundable'}.",
            f"Return: {back.carrier} {back.flight_no}, departs "
            f"{back.depart_utc:%Y-%m-%d %H:%M} UTC.",
            f"Air total ${itinerary.flights.total_usd:,.2f}. "
            f"{itinerary.flights.rationale}",
        ]
    if itinerary.stay:
        hotel = itinerary.stay.recommended
        lines += [
            f"Hotel: {hotel.name}, {hotel.star_rating} star, {hotel.address}, "
            f"{hotel.distance_km_to_venue:.2f} km from the venue, "
            f"${hotel.nightly_rate_usd:,.2f} a night for {hotel.nights} nights, "
            f"${hotel.total_usd:,.2f} total. {itinerary.stay.rationale}",
        ]
    if itinerary.compliance:
        lines.append(f"Policy: {itinerary.compliance.summary}")
        lines += [
            f"  {f.severity}: {f.clause_id} {f.title}: {f.detail}"
            for f in itinerary.compliance.findings
        ]
        if itinerary.compliance.visa:
            visa = itinerary.compliance.visa
            lines.append(
                f"Entry: {visa.requirement.replace('_', ' ')} for a "
                f"{visa.passport_country} passport. {visa.notes}"
            )
    if itinerary.budget:
        lines.append(
            f"Budget: {itinerary.budget.decision}, "
            f"${itinerary.budget.requested_usd:,.2f} against "
            f"{itinerary.budget.cost_center_id}. {itinerary.budget.reason}"
        )
        if itinerary.budget.authorization_code:
            lines.append(
                f"The approval the policy findings asked for has been given. "
                f"Authorisation code {itinerary.budget.authorization_code}. "
                f"Nothing further is required from the traveller."
            )
    lines.append(f"Trip total: ${itinerary.total_usd:,.2f}.")
    return "\n".join(lines)


def plain(itinerary: Itinerary) -> str:
    """The same information without a model, used in deterministic mode."""
    parts = [f"Trip {itinerary.trip_ref}: {itinerary.status.replace('_', ' ')}."]
    if itinerary.flights:
        out = itinerary.flights.outbound
        parts.append(
            f"{out.carrier} {out.flight_no} out and "
            f"{itinerary.flights.inbound.flight_no} back in "
            f"{out.cabin.replace('_', ' ')}, ${itinerary.flights.total_usd:,.2f}."
        )
    if itinerary.stay:
        hotel = itinerary.stay.recommended
        parts.append(
            f"{hotel.nights} nights at {hotel.name}, ${hotel.total_usd:,.2f}."
        )
    if itinerary.compliance:
        parts.append(itinerary.compliance.summary)
    if itinerary.budget:
        parts.append(itinerary.budget.reason)
    parts.append(f"Total ${itinerary.total_usd:,.2f}.")
    return " ".join(parts)
