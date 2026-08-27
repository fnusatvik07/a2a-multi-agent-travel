"""The Concierge's only capability: asking other agents for things.

Every function here is one A2A call. There is no travel logic in this file and
none anywhere else in this service. The Concierge does not know how to price a
fare, read a policy clause or check a budget; it knows who does.

Note that all four calls share one ``context_id``. That is what stitches five
independent processes into a single conversation, and it is why the audit trail
reads as one story rather than five.
"""

from __future__ import annotations

from atlastrip_core.a2a_client import AgentReply, ask
from atlastrip_core.models import (
    FlightBrief,
    ScreeningRequest,
    SpendRequest,
    StayBrief,
)
from atlastrip_core.registry import HEARTH, LEDGER, SENTINEL, SKYLINE

CALLER = "concierge"


async def source_flights(brief: FlightBrief, context_id: str) -> AgentReply:
    return await ask(
        SKYLINE,
        instruction=(
            f"Source a round trip from {brief.origin_iata} to "
            f"{brief.dest_iata}, out {brief.depart_date}, back "
            f"{brief.return_date}, for a grade {brief.traveller_grade} "
            f"traveller. Return your recommendation with alternatives."
        ),
        payload=brief,
        context_id=context_id,
        caller=CALLER,
        trip_ref=brief.trip_ref,
    )


async def source_stay(brief: StayBrief, context_id: str) -> AgentReply:
    hard = (
        " The nightly cap is a hard limit on this request; do not exceed it."
        if brief.enforce_cap
        else ""
    )
    return await ask(
        HEARTH,
        instruction=(
            f"Find a stay in {brief.city} from {brief.check_in} to "
            f"{brief.check_out}, close to venue "
            f"{brief.venue_id or 'the city centre'}.{hard}"
        ),
        payload=brief,
        context_id=context_id,
        caller=CALLER,
        trip_ref=brief.trip_ref,
    )


async def screen_trip(request: ScreeningRequest, context_id: str) -> AgentReply:
    return await ask(
        SENTINEL,
        instruction=(
            "Screen this assembled trip against travel policy and the entry "
            "rulebook. Tell me what is broken and whether a manager has to "
            "sign it off."
        ),
        payload=request,
        context_id=context_id,
        caller=CALLER,
        trip_ref=request.trip_ref,
    )


async def authorise_spend(
    request: SpendRequest, context_id: str, task_id: str | None = None
) -> AgentReply:
    """Ask Ledger to authorise, or resume an authorisation already in flight.

    Passing ``task_id`` continues the task Ledger paused in ``input-required``
    rather than opening a new one, which is how the approval gets back to the
    request it belongs to.
    """
    instruction = (
        "The cost centre owner has approved this trip. Here is the token; "
        "please commit the spend."
        if request.manager_approval_token
        else "Authorise this spend against the cost centre."
    )
    return await ask(
        LEDGER,
        instruction=instruction,
        payload=request,
        context_id=context_id,
        task_id=task_id,
        caller=CALLER,
        trip_ref=request.trip_ref,
    )
