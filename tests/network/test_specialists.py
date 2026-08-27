"""Each specialist, over A2A, doing the job its card advertises."""

from __future__ import annotations

from datetime import date

import pytest

from atlastrip_core import a2a_client
from atlastrip_core.models import (
    BudgetVerdict,
    ComplianceVerdict,
    FlightBrief,
    FlightProposal,
    ScreeningRequest,
    SpendRequest,
    StayBrief,
    StayProposal,
    TravellerProfile,
    TripRequest,
)
from atlastrip_core.registry import HEARTH, LEDGER, SENTINEL, SKYLINE


TRAVELLER = TravellerProfile(
    employee_id=1,
    full_name="Mira Halvorsen",
    email="mira.halvorsen@nimbusrobotics.example",
    title="Staff Robotics Engineer",
    grade="IC5",
    home_iata="SFO",
    passport_country="United States",
    cost_center_id="CC-ROBOTICS-APAC",
    manager_email="elena.marchetti@nimbusrobotics.example",
)


async def source_flights(trip_ref: str, context_id: str) -> FlightProposal:
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source the best round trip.",
        payload=FlightBrief(
            trip_ref=trip_ref, origin_iata="SFO", dest_iata="HND",
            depart_date="2026-10-14", return_date="2026-10-17",
            traveller_grade="IC5", preferred_carriers=["NH", "JL", "UA"],
        ),
        context_id=context_id,
        caller="test",
    )
    assert reply.completed, reply.state
    return FlightProposal.model_validate(reply.data)


async def source_stay(trip_ref: str, context_id: str, enforce: bool) -> StayProposal:
    reply = await a2a_client.ask(
        HEARTH,
        instruction="Find a stay near the venue.",
        payload=StayBrief(
            trip_ref=trip_ref, city="Tokyo", check_in="2026-10-14",
            check_out="2026-10-17", venue_id="KAISEI-HQ",
            nightly_cap_usd=280.0, enforce_cap=enforce, max_distance_km=3.0,
        ),
        context_id=context_id,
        caller="test",
    )
    assert reply.completed, reply.state
    return StayProposal.model_validate(reply.data)


# -- Skyline ----------------------------------------------------------------


async def test_skyline_puts_an_ic5_in_premium_economy_on_a_long_haul(context_id, trip_ref):
    proposal = await source_flights(trip_ref, context_id)
    assert proposal.outbound.cabin == "premium_economy"
    assert proposal.inbound.cabin == "premium_economy"


async def test_skyline_stays_with_the_carriers_it_was_given(context_id, trip_ref):
    proposal = await source_flights(trip_ref, context_id)
    assert {proposal.outbound.carrier, proposal.inbound.carrier} <= {"NH", "JL", "UA"}


async def test_skyline_returns_alternatives_not_just_a_recommendation(context_id, trip_ref):
    assert (await source_flights(trip_ref, context_id)).alternatives


# -- Hearth -----------------------------------------------------------------


async def test_hearth_prefers_the_nearest_room_when_the_cap_is_guidance(context_id, trip_ref):
    """Hearth is allowed to exceed the cap. This is the judgement call that
    makes the renegotiation in the Concierge necessary."""
    stay = await source_stay(trip_ref, context_id, enforce=False)
    assert stay.recommended.name == "Shinagawa Bay Tower"
    assert stay.recommended.nightly_rate_usd > 280.0


async def test_hearth_respects_the_cap_when_told_to_enforce_it(context_id, trip_ref):
    stay = await source_stay(trip_ref, context_id, enforce=True)
    assert stay.recommended.nightly_rate_usd <= 280.0


async def test_hearth_is_still_close_to_the_venue_under_the_cap(context_id, trip_ref):
    stay = await source_stay(trip_ref, context_id, enforce=True)
    assert stay.recommended.distance_km_to_venue < 1.0


# -- Sentinel ---------------------------------------------------------------


async def screen(
    trip_ref: str, context_id: str, flights: FlightProposal, stay: StayProposal
) -> ComplianceVerdict:
    reply = await a2a_client.ask(
        SENTINEL,
        instruction="Screen this trip.",
        payload=ScreeningRequest(
            trip_ref=trip_ref,
            traveller=TRAVELLER,
            request=TripRequest(
                trip_ref=trip_ref, employee_email=TRAVELLER.email, purpose="QBR",
                origin_iata="SFO", destination_iata="HND",
                depart_date="2026-10-14", return_date="2026-10-17",
                venue_id="KAISEI-HQ",
            ),
            flights=flights,
            stay=stay,
            ground_usd=8.40,
            as_of=date(2026, 8, 27),
        ),
        context_id=context_id,
        caller="test",
    )
    assert reply.completed, reply.state
    return ComplianceVerdict.model_validate(reply.data)


async def test_sentinel_catches_the_room_hearth_chose_over_the_cap(context_id, trip_ref):
    flights = await source_flights(trip_ref, context_id)
    stay = await source_stay(trip_ref, context_id, enforce=False)
    verdict = await screen(trip_ref, context_id, flights, stay)

    assert not verdict.compliant
    assert any(
        finding.clause_id == "TRV-003" and finding.severity == "violation"
        for finding in verdict.findings
    )


async def test_sentinel_clears_the_trip_once_the_room_is_under_the_cap(context_id, trip_ref):
    flights = await source_flights(trip_ref, context_id)
    stay = await source_stay(trip_ref, context_id, enforce=True)
    verdict = await screen(trip_ref, context_id, flights, stay)

    assert verdict.compliant
    # Still over the auto-approval threshold, so a human is still needed.
    assert verdict.requires_manager_approval


async def test_sentinel_reports_the_entry_requirement(context_id, trip_ref):
    flights = await source_flights(trip_ref, context_id)
    stay = await source_stay(trip_ref, context_id, enforce=True)
    verdict = await screen(trip_ref, context_id, flights, stay)

    assert verdict.visa is not None
    assert verdict.visa.destination_country == "Japan"
    assert verdict.visa.requirement == "visa_free"


# -- Ledger -----------------------------------------------------------------


def spend(trip_ref: str, **overrides) -> SpendRequest:
    fields = {
        "trip_ref": trip_ref,
        "cost_center_id": "CC-ROBOTICS-APAC",
        "employee_email": TRAVELLER.email,
        "flights_usd": 3110.48,
        "lodging_usd": 569.88,
        "ground_usd": 8.40,
    }
    fields.update(overrides)
    return SpendRequest(**fields)


async def test_ledger_pauses_the_task_when_a_human_is_needed(context_id, trip_ref):
    reply = await a2a_client.ask(
        LEDGER,
        instruction="Authorise this spend.",
        payload=spend(trip_ref, requires_manager_approval=True),
        context_id=context_id,
        caller="test",
    )
    assert reply.state == "TASK_STATE_INPUT_REQUIRED"
    assert reply.task_id

    verdict = BudgetVerdict.model_validate(reply.data)
    assert verdict.decision == "needs_approval"
    assert verdict.approval_token


async def test_the_approval_settles_the_same_task(context_id, trip_ref):
    """This is the whole human-in-the-loop mechanism: one task, two turns."""
    request = spend(trip_ref, requires_manager_approval=True)
    paused = await a2a_client.ask(
        LEDGER, instruction="Authorise this spend.", payload=request,
        context_id=context_id, caller="test",
    )
    token = BudgetVerdict.model_validate(paused.data).approval_token

    settled = await a2a_client.ask(
        LEDGER,
        instruction="Approved; please commit.",
        payload=request.model_copy(update={"manager_approval_token": token}),
        context_id=context_id,
        task_id=paused.task_id,
        caller="test",
    )
    assert settled.task_id == paused.task_id
    assert settled.state == "TASK_STATE_COMPLETED"

    verdict = BudgetVerdict.model_validate(settled.data)
    assert verdict.decision == "approved"
    assert verdict.authorization_code == token


async def test_a_small_trip_needs_no_human_at_all(context_id, trip_ref):
    reply = await a2a_client.ask(
        LEDGER,
        instruction="Authorise this spend.",
        payload=spend(trip_ref, flights_usd=400.0, lodging_usd=200.0, ground_usd=10.0),
        context_id=context_id,
        caller="test",
    )
    assert reply.completed
    assert BudgetVerdict.model_validate(reply.data).decision == "approved"


async def test_a_trip_beyond_the_budget_is_rejected(context_id, trip_ref):
    reply = await a2a_client.ask(
        LEDGER,
        instruction="Authorise this spend.",
        payload=spend(trip_ref, flights_usd=500_000.0),
        context_id=context_id,
        caller="test",
    )
    assert reply.completed
    verdict = BudgetVerdict.model_validate(reply.data)
    assert verdict.decision == "rejected"
    assert verdict.authorization_code is None
