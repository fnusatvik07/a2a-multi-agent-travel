"""The state the Concierge's graph carries from node to node."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from atlastrip_core.models import (
    BudgetVerdict,
    ComplianceVerdict,
    FlightProposal,
    StayProposal,
    TravellerProfile,
    TripRequest,
)


def append(existing: list[str], incoming: list[str]) -> list[str]:
    """Reducer: narration accumulates instead of being overwritten.

    Two nodes run concurrently in this graph, so without a reducer LangGraph
    would reject their simultaneous writes to the same key.
    """
    return [*existing, *incoming]


class TripState(TypedDict, total=False):
    """One trip, as it moves through the graph.

    Everything the four specialists send back lands here, which makes the
    state a complete record of the negotiation: what was asked, what came
    back, what was overruled, and what was finally agreed.
    """

    # Set on entry
    utterance: str
    """What the traveller actually typed."""
    trip_ref: str
    context_id: str
    """The A2A context id shared by every call this trip makes."""

    # Filled by intake
    request: TripRequest
    traveller: TravellerProfile
    ground_usd: float
    ground_note: str

    # Filled by the specialists
    flights: FlightProposal
    stay: StayProposal
    compliance: ComplianceVerdict
    budget: BudgetVerdict

    # Negotiation bookkeeping
    ledger_task_id: str
    approval_token: str
    renegotiated: bool
    """True once the stay has been re-sourced under an enforced cap."""

    # Output
    status: str
    narrative: str
    journal: Annotated[list[str], append]
    """Human-readable trace, streamed back to the caller as progress."""
    error: str
