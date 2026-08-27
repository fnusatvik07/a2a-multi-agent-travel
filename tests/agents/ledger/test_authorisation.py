"""Ledger is the only agent that spends money, so its decisions are pinned down.

The MCP calls are stubbed here: these tests are about the decision, not about
the inventory server. The live path is covered by tests/network.
"""

from __future__ import annotations

import pytest
from ledger_pydanticai import service

from atlastrip_core.models import SpendRequest


@pytest.fixture
def budget(monkeypatch):
    """Set the cost centre's remaining balance, and record any commitment."""
    committed: list[float] = []

    def set_remaining(remaining: float) -> list[float]:
        async def position(_: str) -> dict[str, float]:
            return {"remaining_usd": remaining}

        async def commit(request: SpendRequest, total: float) -> None:
            committed.append(total)

        monkeypatch.setattr(service, "budget_position", position)
        monkeypatch.setattr(service, "_commit", commit)
        return committed

    return set_remaining


def spend(**overrides) -> SpendRequest:
    fields = {
        "trip_ref": "TRIP-1",
        "cost_center_id": "CC-ROBOTICS-APAC",
        "employee_email": "mira.halvorsen@nimbusrobotics.example",
        "flights_usd": 3110.48,
        "lodging_usd": 569.88,
        "ground_usd": 8.40,
    }
    fields.update(overrides)
    return SpendRequest(**fields)


async def test_a_small_trip_is_approved_and_committed_without_a_human(budget):
    committed = budget(7600.0)
    verdict = await service.assess(spend(flights_usd=500.0, lodging_usd=200.0))

    assert verdict.decision == "approved"
    assert verdict.authorization_code
    assert committed == [708.4]


async def test_a_trip_needing_approval_pauses_and_spends_nothing(budget):
    committed = budget(7600.0)
    verdict = await service.assess(spend(requires_manager_approval=True))

    assert verdict.decision == "needs_approval"
    assert verdict.authorization_code is None
    assert verdict.approval_token, "the caller needs a token to come back with"
    assert committed == [], "no money moves before a human says yes"


async def test_the_pending_token_settles_the_request_on_the_next_turn(budget):
    committed = budget(7600.0)
    request = spend(requires_manager_approval=True)
    paused = await service.assess(request)

    approved = await service.assess(
        request.model_copy(update={"manager_approval_token": paused.approval_token})
    )
    assert approved.decision == "approved"
    assert approved.authorization_code == paused.approval_token
    assert committed == [3688.76]


async def test_a_wrong_token_does_not_unlock_the_spend(budget):
    """The token is a correlation, but it still has to be the right one."""
    committed = budget(7600.0)
    verdict = await service.assess(
        spend(requires_manager_approval=True, manager_approval_token="AUTH-GUESS")
    )
    assert verdict.decision == "needs_approval"
    assert committed == []


async def test_a_trip_larger_than_the_budget_is_rejected_outright(budget):
    """No level of approval can spend money the cost centre does not have."""
    committed = budget(1000.0)
    verdict = await service.assess(spend(requires_manager_approval=True))

    assert verdict.decision == "rejected"
    assert committed == []
    assert verdict.remaining_after_usd == 1000.0


async def test_a_rejection_still_reports_the_position_it_was_measured_against(budget):
    budget(1000.0)
    verdict = await service.assess(spend())
    assert verdict.remaining_before_usd == 1000.0
    assert "$1,000.00" in verdict.reason


async def test_the_remaining_balance_is_only_reduced_on_an_approval(budget):
    budget(7600.0)
    paused = await service.assess(spend(requires_manager_approval=True))
    assert paused.remaining_after_usd == paused.remaining_before_usd


async def test_the_authorisation_code_is_stable_for_the_same_request():
    """A replayed authorisation must not mint a second code for one trip."""
    request = spend()
    assert service.authorization_code(request) == service.authorization_code(request)


async def test_the_authorisation_code_changes_when_the_amount_does():
    """If the trip is re-costed, the old approval should not carry over."""
    first = service.authorization_code(spend())
    second = service.authorization_code(spend(lodging_usd=894.99))
    assert first != second


async def test_a_trip_that_exactly_exhausts_the_budget_is_still_allowed(budget):
    committed = budget(3688.76)
    verdict = await service.assess(spend())
    assert verdict.decision == "approved"
    assert verdict.remaining_after_usd == 0.0
    assert committed == [3688.76]
