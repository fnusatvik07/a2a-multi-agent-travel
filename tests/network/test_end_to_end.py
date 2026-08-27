"""The whole network, from one sentence to a confirmed itinerary.

This is the test that says the project works. It goes through the Concierge
and nothing else, exactly as the CLI does, and it exercises every part of the
story: the parallel fan-out, the compliance gate, the renegotiation with
Hearth, the human approval, and the commitment to the ledger.
"""

from __future__ import annotations

import pytest

from atlastrip_core import a2a_client, audit
from atlastrip_core.models import Itinerary
from atlastrip_core.registry import CONCIERGE

REQUEST = (
    "Mira Halvorsen needs to be at the Kaisei Robotics quarterly business "
    "review in Tokyo from 14 October 2026 to 17 October 2026."
)


async def plan(context_id: str, trip_ref: str):
    return await a2a_client.ask(
        CONCIERGE,
        instruction=REQUEST,
        payload={"trip_ref": trip_ref},
        context_id=context_id,
        caller="test",
        trip_ref=trip_ref,
    )


async def answer(context_id: str, trip_ref: str, task_id: str, approved: bool):
    return await a2a_client.ask(
        CONCIERGE,
        instruction="approve" if approved else "decline",
        payload={"approved": approved},
        context_id=context_id,
        task_id=task_id,
        caller="test",
        trip_ref=trip_ref,
    )


@pytest.fixture(scope="module")
async def approved_trip(request):
    """One full run, shared by the assertions below.

    Module scoped because it costs about a minute and a handful of model
    calls; splitting it into one run per assertion would buy nothing.
    """
    import uuid

    context_id = f"ctx-test-{uuid.uuid4().hex[:12]}"
    trip_ref = f"TEST-{uuid.uuid4().hex[:8].upper()}"

    first = await plan(context_id, trip_ref)
    assert first.state == "TASK_STATE_INPUT_REQUIRED", (
        f"expected the trip to stop for approval, got {first.state}"
    )
    second = await answer(context_id, trip_ref, first.task_id, approved=True)
    assert second.completed, second.state

    return {
        "context_id": context_id,
        "trip_ref": trip_ref,
        "paused": first,
        "settled": second,
        "itinerary": Itinerary.model_validate(second.data),
    }


async def test_the_trip_stops_for_a_human_before_anything_is_ticketed(approved_trip):
    assert approved_trip["paused"].state == "TASK_STATE_INPUT_REQUIRED"
    assert "approve" in approved_trip["paused"].question.lower()


async def test_the_approval_lands_on_the_task_that_was_paused(approved_trip):
    assert approved_trip["settled"].task_id == approved_trip["paused"].task_id


async def test_the_trip_is_confirmed_once_it_is_approved(approved_trip):
    itinerary = approved_trip["itinerary"]
    assert itinerary.status == "confirmed"
    assert itinerary.budget is not None
    assert itinerary.budget.decision == "approved"
    assert itinerary.budget.authorization_code


async def test_the_itinerary_carries_every_specialists_work(approved_trip):
    itinerary = approved_trip["itinerary"]
    assert itinerary.flights is not None, "Skyline"
    assert itinerary.stay is not None, "Hearth"
    assert itinerary.compliance is not None, "Sentinel"
    assert itinerary.budget is not None, "Ledger"


async def test_the_stay_that_ships_is_the_renegotiated_one(approved_trip):
    """Hearth's first answer broke the cap; the one on the itinerary must not."""
    stay = approved_trip["itinerary"].stay
    assert stay.recommended.nightly_rate_usd <= 280.0


async def test_the_final_trip_is_within_policy(approved_trip):
    assert approved_trip["itinerary"].compliance.compliant


async def test_the_total_is_the_sum_of_its_parts(approved_trip):
    itinerary = approved_trip["itinerary"]
    expected = round(
        itinerary.flights.total_usd + itinerary.stay.total_usd
        + itinerary.budget.breakdown.get("ground_usd", 0.0),
        2,
    )
    assert itinerary.total_usd == pytest.approx(expected, abs=0.01)


async def test_the_money_matches_what_ledger_was_asked_to_authorise(approved_trip):
    itinerary = approved_trip["itinerary"]
    assert itinerary.budget.requested_usd == pytest.approx(
        itinerary.total_usd, abs=0.01
    )


async def test_the_narrative_is_written_for_a_person(approved_trip):
    narrative = approved_trip["itinerary"].narrative
    assert len(narrative) > 120
    assert approved_trip["itinerary"].stay.recommended.name in narrative


async def test_one_context_id_ties_all_five_agents_together(approved_trip):
    """The point of the context id: five processes, one readable story."""
    trail = audit.trail(approved_trip["context_id"])
    agents = {entry["agent"] for entry in trail}
    assert {"concierge", "skyline", "hearth", "sentinel", "ledger"} <= agents


async def test_the_trail_shows_hearth_being_asked_twice(approved_trip):
    """Once on judgement, once with the cap enforced. That is the negotiation."""
    trail = audit.trail(approved_trip["context_id"])
    asks = [
        entry
        for entry in trail
        if entry["agent"] == "hearth" and entry["event"] == "received"
    ]
    assert len(asks) == 2
    assert "cap enforced" in asks[1]["summary"]


async def test_the_trail_records_the_escalation_to_a_human(approved_trip):
    trail = audit.trail(approved_trip["context_id"])
    escalations = {
        entry["agent"] for entry in trail if entry["event"] == "escalated"
    }
    # Ledger raised it; the Concierge passed it on rather than deciding itself.
    assert {"ledger", "concierge"} <= escalations


async def test_a_declined_trip_is_not_ticketed(context_id, trip_ref):
    """The other branch: a human can say no, and nothing is committed."""
    paused = await plan(context_id, trip_ref)
    assert paused.state == "TASK_STATE_INPUT_REQUIRED"

    declined = await answer(context_id, trip_ref, paused.task_id, approved=False)
    assert declined.state == "TASK_STATE_FAILED"
    assert "declined" in declined.question.lower()
