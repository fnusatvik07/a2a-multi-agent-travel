"""The shared vocabulary is a contract, so it gets tested like one."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from atlastrip_core.models import (
    BudgetVerdict,
    FlightBrief,
    FlightOffer,
    FlightProposal,
    SpendRequest,
    TripRequest,
)


def test_trip_request_counts_nights_not_days():
    request = TripRequest(
        trip_ref="TRIP-1",
        employee_email="a@b.example",
        purpose="QBR",
        origin_iata="SFO",
        destination_iata="HND",
        depart_date=date(2026, 10, 14),
        return_date=date(2026, 10, 17),
    )
    assert request.nights == 3


def test_trip_request_never_reports_zero_nights():
    """A same-day return still needs one night priced, or the stay is free."""
    request = TripRequest(
        trip_ref="TRIP-1",
        employee_email="a@b.example",
        purpose="Day trip",
        origin_iata="SFO",
        destination_iata="JFK",
        depart_date=date(2026, 9, 15),
        return_date=date(2026, 9, 15),
    )
    assert request.nights == 1


def test_spend_request_total_is_the_sum_of_its_parts():
    spend = SpendRequest(
        trip_ref="TRIP-1",
        cost_center_id="CC-1",
        employee_email="a@b.example",
        flights_usd=3110.48,
        lodging_usd=569.88,
        ground_usd=8.40,
    )
    assert spend.total_usd == 3688.76


def test_payloads_reject_unknown_fields():
    """A typo in a field name must fail loudly rather than travel silently."""
    with pytest.raises(ValidationError):
        FlightBrief(
            trip_ref="TRIP-1",
            origin_iata="SFO",
            dest_iata="HND",
            depart_date=date(2026, 10, 14),
            return_date=date(2026, 10, 17),
            traveller_grade="IC5",
            prefered_carriers=["UA"],  # misspelled on purpose
        )


def test_a_proposal_survives_a_json_round_trip():
    """Every payload crosses the wire as JSON, so this is the real test."""
    leg = FlightOffer(
        offer_id="FL-1",
        direction="outbound",
        carrier="UA",
        flight_no="UA 837",
        origin_iata="SFO",
        dest_iata="HND",
        depart_utc=datetime(2026, 10, 14, 17, 55),
        arrive_utc=datetime(2026, 10, 15, 5, 10),
        duration_minutes=675,
        stops=0,
        cabin="premium_economy",
        fare_basis="UA-PRE-SAVER",
        total_usd=1648.36,
        refundable=False,
        co2_kg=1192.3,
        aircraft="Boeing 777-200ER",
    )
    proposal = FlightProposal(
        trip_ref="TRIP-1",
        outbound=leg,
        inbound=leg.model_copy(update={"direction": "return", "offer_id": "FL-2"}),
        total_usd=3296.72,
    )
    restored = FlightProposal.model_validate(proposal.model_dump(mode="json"))
    assert restored == proposal


def test_budget_verdict_separates_a_pending_token_from_an_issued_code():
    """Confusing these two would let an unapproved trip look authorised."""
    pending = BudgetVerdict(
        trip_ref="TRIP-1",
        cost_center_id="CC-1",
        requested_usd=3688.76,
        remaining_before_usd=7600.0,
        remaining_after_usd=7600.0,
        decision="needs_approval",
        reason="Needs sign-off.",
        approval_token="AUTH-ABC",
    )
    assert pending.authorization_code is None
    assert pending.approval_token == "AUTH-ABC"


def test_a_message_survives_an_exception_that_has_no_message():
    """httpx.ReadTimeout and friends stringify to "", which produced agent
    failures that said nothing at all."""
    from atlastrip_core.a2a_support import describe

    assert describe(TimeoutError()) == "TimeoutError"
    assert describe(ValueError("bad brief")) == "ValueError: bad brief"
