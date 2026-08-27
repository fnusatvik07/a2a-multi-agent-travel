"""The Concierge's orchestration, as an explicit LangGraph state machine.

The shape of the graph is the shape of the business process, which is the
reason for using LangGraph here rather than a tool-calling loop: booking a trip
is not an open-ended conversation, it is a workflow with a fan-out, a
compliance gate, one renegotiation and a human approval.

    intake ─▶ source ─▶ screen ─┬─ not compliant, first time ─▶ renegotiate ─┐
                          ▲     │                                            │
                          └─────┴────────────────────────────────────────────┘
                                │
                                └─ compliant, or already renegotiated
                                        │
                                        ▼
                                   authorise ─┬─ approved ────────▶ assemble ─▶ END
                                              └─ needs approval ─▶ await_approval
                                                                        │
                                                                   (interrupt)
                                                                        │
                                                                   confirm ─▶ assemble

``source`` fans out to Skyline and Hearth at the same time. ``await_approval``
suspends the whole graph on a LangGraph ``interrupt`` while a person decides;
the Concierge's own A2A task goes to ``input-required`` at the same moment, so
the pause is visible all the way out to whoever asked for the trip.
"""

from __future__ import annotations

import asyncio

from datetime import date

from atlastrip_core.console import get_logger
from atlastrip_core.models import (
    BudgetVerdict,
    ComplianceVerdict,
    FlightBrief,
    FlightProposal,
    Itinerary,
    ScreeningRequest,
    SpendRequest,
    StayBrief,
    StayProposal,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import intake, narrative, network
from .state import TripState


log = get_logger("concierge")

# How close to the customer's site the traveller should be. Passed to Hearth as
# part of the brief; Hearth decides what to do inside it.
MAX_VENUE_DISTANCE_KM = 3.0

PREFERRED_CARRIERS = ["NH", "JL", "UA", "BA", "SQ", "DL", "AI"]

# The nightly cap the Concierge passes on as guidance. It is Sentinel that
# holds the authoritative version; this is a hint so Hearth is not searching
# blind, and Hearth is free to exceed it on the first pass.
TOKYO_TIER_CAP_HINT = 280.0


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------


async def node_intake(state: TripState) -> TripState:
    """Turn free text into a trip request and resolve who is travelling."""
    request = await intake.parse(state["utterance"], state["trip_ref"])
    traveller = await intake.lookup_traveller(request.employee_email)
    ground_usd, ground_note = await intake.cheapest_ground(
        await _destination_city(request.destination_iata)
    )
    log.info(
        "%s: %s %s->%s %s..%s",
        state["trip_ref"],
        traveller.full_name,
        request.origin_iata,
        request.destination_iata,
        request.depart_date,
        request.return_date,
    )
    return {
        "request": request,
        "traveller": traveller,
        "ground_usd": ground_usd,
        "ground_note": ground_note,
        "journal": [
            f"Understood: {traveller.full_name} ({traveller.grade}), "
            f"{request.origin_iata} to {request.destination_iata}, "
            f"{request.depart_date} to {request.return_date}, for "
            f"{request.purpose}."
        ],
    }


async def node_source(state: TripState) -> TripState:
    """Ask Skyline and Hearth at the same time.

    Two agents, two processes, two frameworks, one ``asyncio.gather``. Neither
    knows the other exists.
    """
    request = state["request"]
    traveller = state["traveller"]
    city = await _destination_city(request.destination_iata)

    flight_brief = FlightBrief(
        trip_ref=request.trip_ref,
        origin_iata=request.origin_iata,
        dest_iata=request.destination_iata,
        depart_date=request.depart_date,
        return_date=request.return_date,
        traveller_grade=traveller.grade,
        preferred_carriers=PREFERRED_CARRIERS,
    )
    stay_brief = StayBrief(
        trip_ref=request.trip_ref,
        city=city,
        check_in=request.depart_date,
        check_out=request.return_date,
        venue_id=request.venue_id,
        nightly_cap_usd=TOKYO_TIER_CAP_HINT,
        max_distance_km=MAX_VENUE_DISTANCE_KM,
    )

    flights_reply, stay_reply = await asyncio.gather(
        network.source_flights(flight_brief, state["context_id"]),
        network.source_stay(stay_brief, state["context_id"]),
    )

    if not flights_reply.completed or not stay_reply.completed:
        return {
            "error": _failure_text(flights_reply, stay_reply),
            "journal": ["Sourcing failed."],
        }

    flights = FlightProposal.model_validate(flights_reply.data)
    stay = StayProposal.model_validate(stay_reply.data)
    return {
        "flights": flights,
        "stay": stay,
        "journal": [
            f"Skyline: {flights.outbound.carrier} {flights.outbound.flight_no} / "
            f"{flights.inbound.flight_no} in "
            f"{flights.outbound.cabin.replace('_', ' ')}, "
            f"${flights.total_usd:,.2f}.",
            f"Hearth: {stay.recommended.name}, "
            f"${stay.recommended.nightly_rate_usd:,.2f} a night, "
            f"${stay.total_usd:,.2f}.",
        ],
    }


async def node_screen(state: TripState) -> TripState:
    """Send the assembled trip to Sentinel and take its ruling as binding."""
    screening = ScreeningRequest(
        trip_ref=state["trip_ref"],
        traveller=state["traveller"],
        request=state["request"],
        flights=state["flights"],
        stay=state["stay"],
        ground_usd=state.get("ground_usd", 0.0),
        as_of=date.today(),
    )
    reply = await network.screen_trip(screening, state["context_id"])
    if not reply.completed:
        return {"error": f"Sentinel could not screen the trip: {reply.state}"}

    verdict = ComplianceVerdict.model_validate(reply.data)
    lines = [f"Sentinel: {verdict.summary}"]
    lines += [
        f"  {finding.severity}: {finding.clause_id} {finding.detail}"
        for finding in verdict.findings
        if finding.severity != "info"
    ]
    return {"compliance": verdict, "journal": lines}


async def node_renegotiate(state: TripState) -> TripState:
    """Go back to Hearth with the cap as a hard constraint.

    This is the negotiation the architecture exists to make possible. Hearth
    made a defensible judgement, Sentinel overruled it, and rather than the
    Concierge quietly overriding either of them, it asks again with the
    constraint that was actually broken.
    """
    request = state["request"]
    cap = _breached_lodging_cap(state["compliance"]) or TOKYO_TIER_CAP_HINT
    brief = StayBrief(
        trip_ref=request.trip_ref,
        city=state["stay"].recommended.city,
        check_in=request.depart_date,
        check_out=request.return_date,
        venue_id=request.venue_id,
        nightly_cap_usd=cap,
        enforce_cap=True,
        max_distance_km=MAX_VENUE_DISTANCE_KM,
    )
    reply = await network.source_stay(brief, state["context_id"])
    if not reply.completed:
        return {
            "error": f"No compliant stay is available under ${cap:,.2f} a night.",
            "renegotiated": True,
        }

    stay = StayProposal.model_validate(reply.data)
    return {
        "stay": stay,
        "renegotiated": True,
        "journal": [
            f"Re-asked Hearth with the ${cap:,.2f} cap enforced: "
            f"{stay.recommended.name}, "
            f"${stay.recommended.nightly_rate_usd:,.2f} a night, "
            f"${stay.total_usd:,.2f}."
        ],
    }


async def node_authorise(state: TripState) -> TripState:
    """Ask Ledger for the money."""
    reply = await network.authorise_spend(_spend_request(state), state["context_id"])
    if reply.data is None:
        return {"error": f"Ledger did not return a verdict: {reply.state}"}

    verdict = BudgetVerdict.model_validate(reply.data)
    return {
        "budget": verdict,
        "ledger_task_id": reply.task_id,
        "journal": [f"Ledger: {verdict.decision}. {verdict.reason}"],
    }


def node_await_approval(state: TripState) -> TripState:
    """Suspend the graph until a human decides.

    ``interrupt`` stops execution here and hands the payload out to whoever is
    running the graph. The executor turns that into an A2A ``input-required``
    status on the Concierge's own task, so the pause travels all the way back
    to the caller. When the answer arrives the graph resumes at this node and
    the returned value is whatever was sent in.
    """
    verdict = state["budget"]
    decision = interrupt(
        {
            "question": (
                f"{verdict.reason} Approve ${verdict.requested_usd:,.2f} "
                f"against {verdict.cost_center_id}?"
            ),
            "trip_ref": state["trip_ref"],
            "amount_usd": verdict.requested_usd,
            "cost_center_id": verdict.cost_center_id,
            "approver": state["traveller"].manager_email,
        }
    )

    approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
    if not approved:
        return {
            "error": "The cost centre owner declined this trip.",
            "journal": ["Approval declined. Nothing was ticketed."],
        }
    # Ledger told us, when it paused, which token would settle the task.
    return {
        "approval_token": verdict.approval_token or "",
        "journal": ["Approval received. Returning to Ledger."],
    }


async def node_confirm(state: TripState) -> TripState:
    """Take the approval back to Ledger, on the task it paused."""
    request = _spend_request(state)
    request = request.model_copy(
        update={"manager_approval_token": state.get("approval_token")}
    )
    reply = await network.authorise_spend(
        request, state["context_id"], task_id=state.get("ledger_task_id")
    )
    if reply.data is None:
        return {"error": f"Ledger did not settle the authorisation: {reply.state}"}

    verdict = BudgetVerdict.model_validate(reply.data)
    return {
        "budget": verdict,
        "journal": [f"Ledger: {verdict.decision}. {verdict.reason}"],
    }


async def node_assemble(state: TripState) -> TripState:
    """Write the itinerary the traveller actually receives."""
    itinerary = build_itinerary(state)
    itinerary.narrative = await narrative.write(itinerary)
    return {
        "status": itinerary.status,
        "narrative": itinerary.narrative,
        "journal": [f"Itinerary {itinerary.status}, ${itinerary.total_usd:,.2f}."],
    }


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------


def after_source(state: TripState) -> str:
    return END if state.get("error") else "screen"


def after_screen(state: TripState) -> str:
    """Renegotiate once, if the thing that broke is something Hearth can fix."""
    if state.get("error"):
        return END
    verdict = state["compliance"]
    if (
        not verdict.compliant
        and not state.get("renegotiated")
        and _breached_lodging_cap(verdict) is not None
    ):
        return "renegotiate"
    return "authorise"


def after_renegotiate(state: TripState) -> str:
    return END if state.get("error") else "screen"


def after_authorise(state: TripState) -> str:
    if state.get("error"):
        return END
    return (
        "await_approval"
        if state["budget"].decision == "needs_approval"
        else "assemble"
    )


def after_await_approval(state: TripState) -> str:
    return END if state.get("error") else "confirm"


def after_confirm(state: TripState) -> str:
    return END if state.get("error") else "assemble"


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def build_graph() -> StateGraph:
    graph = StateGraph(TripState)
    graph.add_node("intake", node_intake)
    graph.add_node("source", node_source)
    graph.add_node("screen", node_screen)
    graph.add_node("renegotiate", node_renegotiate)
    graph.add_node("authorise", node_authorise)
    graph.add_node("await_approval", node_await_approval)
    graph.add_node("confirm", node_confirm)
    graph.add_node("assemble", node_assemble)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "source")
    graph.add_conditional_edges("source", after_source, ["screen", END])
    graph.add_conditional_edges("screen", after_screen, ["renegotiate", "authorise", END])
    graph.add_conditional_edges("renegotiate", after_renegotiate, ["screen", END])
    graph.add_conditional_edges("authorise", after_authorise, ["await_approval", "assemble", END])
    graph.add_conditional_edges("await_approval", after_await_approval, ["confirm", END])
    graph.add_conditional_edges("confirm", after_confirm, ["assemble", END])
    graph.add_edge("assemble", END)
    return graph


def compile_graph():
    """Compile with a checkpointer, which is what makes ``interrupt`` possible.

    The checkpoint lives in memory: a Concierge restart loses trips that are
    mid-approval. The A2A task itself is in Postgres, so the task survives;
    swapping ``MemorySaver`` for the Postgres checkpointer would make the graph
    survive too.
    """
    return build_graph().compile(checkpointer=MemorySaver())


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _spend_request(state: TripState) -> SpendRequest:
    compliance = state.get("compliance")
    return SpendRequest(
        trip_ref=state["trip_ref"],
        cost_center_id=state["traveller"].cost_center_id,
        employee_email=state["traveller"].email,
        flights_usd=state["flights"].total_usd,
        lodging_usd=state["stay"].total_usd,
        ground_usd=state.get("ground_usd", 0.0),
        requires_manager_approval=bool(
            compliance and compliance.requires_manager_approval
        ),
    )


def _breached_lodging_cap(verdict: ComplianceVerdict) -> float | None:
    """The cap from a lodging violation, if there is one.

    Sentinel states the cap in the finding's detail, so the Concierge does not
    have to hold a copy of the policy in order to act on the ruling.
    """
    import re

    for finding in verdict.findings:
        if finding.clause_id == "TRV-003" and finding.severity == "violation":
            match = re.search(r"cap of \$([\d,]+(?:\.\d+)?)", finding.detail)
            if match:
                return float(match.group(1).replace(",", ""))
    return None


def build_itinerary(state: TripState) -> Itinerary:
    from datetime import datetime, timezone

    budget = state.get("budget")
    compliance = state.get("compliance")
    total = round(
        state["flights"].total_usd
        + state["stay"].total_usd
        + state.get("ground_usd", 0.0),
        2,
    )
    if budget is None:
        status = "rejected"
    elif budget.decision == "approved":
        status = "confirmed"
    elif budget.decision == "needs_approval":
        status = "awaiting_approval"
    else:
        status = "rejected"

    return Itinerary(
        trip_ref=state["trip_ref"],
        status=status,  # type: ignore[arg-type]
        traveller=state["traveller"],
        request=state["request"],
        flights=state["flights"],
        stay=state["stay"],
        compliance=compliance,
        budget=budget,
        total_usd=total,
        generated_at=datetime.now(timezone.utc),
    )


async def _destination_city(iata: str) -> str:
    from atlastrip_core.mcp_http import MCPClient

    async with MCPClient() as mcp:
        airports = await mcp.call("list_airports")
    for airport in airports:
        if airport["iata"] == iata.upper():
            return airport["city"]
    return iata.upper()


def _failure_text(*replies) -> str:
    parts = [
        f"{reply.agent} returned {reply.state}"
        + (f": {reply.question}" if reply.question else "")
        for reply in replies
        if not reply.completed
    ]
    return "; ".join(parts)
