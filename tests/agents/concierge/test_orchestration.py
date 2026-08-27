"""The Concierge's routing: which node runs next, and why.

These are the decisions that make the negotiation happen, so they are tested
without a network, a model or any of the other four agents.
"""

from __future__ import annotations

from datetime import date, datetime

from atlastrip_core.models import (
    BudgetVerdict,
    ComplianceVerdict,
    FlightOffer,
    FlightProposal,
    HotelOffer,
    PolicyFinding,
    StayProposal,
    TravellerProfile,
    TripRequest,
)
from concierge_langgraph import executor, graph
from langgraph.graph import END


def verdict(compliant: bool, findings: list[PolicyFinding], approval: bool = False):
    return ComplianceVerdict(
        trip_ref="TRIP-1",
        compliant=compliant,
        findings=findings,
        requires_manager_approval=approval,
    )


def lodging_breach(cap: float = 280.0) -> PolicyFinding:
    return PolicyFinding(
        clause_id="TRV-003",
        title="Lodging nightly cap",
        severity="violation",
        detail=(
            f"Shinagawa Bay Tower is $298.33 a night against a Tokyo cap of "
            f"${cap:,.2f}, an overage of $18.33 a night."
        ),
        requires_approval=True,
    )


def cabin_breach() -> PolicyFinding:
    return PolicyFinding(
        clause_id="TRV-001",
        title="Cabin entitlement",
        severity="violation",
        detail="Booked above entitlement.",
        requires_approval=True,
    )


# -- the compliance gate ----------------------------------------------------


def test_a_compliant_trip_goes_straight_to_the_budget():
    assert graph.after_screen({"compliance": verdict(True, [])}) == "authorise"


def test_a_lodging_breach_sends_the_trip_back_to_hearth():
    state = {"compliance": verdict(False, [lodging_breach()])}
    assert graph.after_screen(state) == "renegotiate"


def test_the_trip_is_only_renegotiated_once():
    """Otherwise a cap nobody can meet would loop between two agents forever."""
    state = {"compliance": verdict(False, [lodging_breach()]), "renegotiated": True}
    assert graph.after_screen(state) == "authorise"


def test_a_breach_hearth_cannot_fix_is_not_sent_back_to_hearth():
    state = {"compliance": verdict(False, [cabin_breach()])}
    assert graph.after_screen(state) == "authorise"


def test_a_sourcing_failure_ends_the_run():
    assert graph.after_source({"error": "Skyline is down"}) == END
    assert graph.after_screen({"error": "Sentinel is down"}) == END


# -- reading the cap back out of the ruling ---------------------------------


def test_the_cap_is_read_out_of_sentinels_finding():
    """The Concierge holds no copy of the policy; it acts on what it was told."""
    assert graph._breached_lodging_cap(verdict(False, [lodging_breach(280.0)])) == 280.0


def test_a_cap_with_a_thousands_separator_is_read_correctly():
    assert graph._breached_lodging_cap(verdict(False, [lodging_breach(1250.0)])) == 1250.0


def test_no_lodging_breach_means_no_cap_to_enforce():
    assert graph._breached_lodging_cap(verdict(False, [cabin_breach()])) is None


def test_a_lodging_finding_that_is_only_a_warning_is_not_a_breach():
    warning = lodging_breach()
    warning = warning.model_copy(update={"severity": "warning"})
    assert graph._breached_lodging_cap(verdict(True, [warning])) is None


# -- the approval gate ------------------------------------------------------


def budget(decision: str) -> BudgetVerdict:
    return BudgetVerdict(
        trip_ref="TRIP-1",
        cost_center_id="CC-1",
        requested_usd=3688.76,
        remaining_before_usd=7600.0,
        remaining_after_usd=7600.0,
        decision=decision,  # type: ignore[arg-type]
        reason="",
        approval_token="AUTH-ABC" if decision == "needs_approval" else None,
    )


def test_an_approved_budget_goes_straight_to_the_itinerary():
    assert graph.after_authorise({"budget": budget("approved")}) == "assemble"


def test_a_budget_needing_sign_off_suspends_the_graph():
    assert graph.after_authorise({"budget": budget("needs_approval")}) == "await_approval"


def test_a_rejected_budget_still_produces_an_itinerary_saying_so():
    assert graph.after_authorise({"budget": budget("rejected")}) == "assemble"


def test_a_declined_approval_ends_the_run_without_ticketing():
    assert graph.after_await_approval({"error": "declined"}) == END


def test_an_approval_continues_to_ledger():
    assert graph.after_await_approval({"approval_token": "AUTH-ABC"}) == "confirm"


# -- reading the human's answer ---------------------------------------------


def test_a_structured_answer_is_taken_at_face_value():
    assert executor._read_decision("", {"approved": True}) == {"approved": True}
    assert executor._read_decision("", {"approved": False}) == {"approved": False}


def test_plain_english_approval_is_understood():
    assert executor._read_decision("approve", {})["approved"]
    assert executor._read_decision("yes, go ahead", {})["approved"]


def test_plain_english_refusal_is_understood():
    assert not executor._read_decision("decline", {})["approved"]
    assert not executor._read_decision("no", {})["approved"]
    assert not executor._read_decision("Cancel it.", {})["approved"]


def test_the_structured_answer_wins_over_the_words():
    """A UI that sends both should not be second-guessed by a keyword match."""
    assert not executor._read_decision("approve", {"approved": False})["approved"]


# -- the itinerary ----------------------------------------------------------


def sample_state() -> dict:
    leg = FlightOffer(
        offer_id="FL-1", direction="outbound", carrier="UA", flight_no="UA 837",
        origin_iata="SFO", dest_iata="HND",
        depart_utc=datetime(2026, 10, 14, 17, 55),
        arrive_utc=datetime(2026, 10, 15, 5, 10), duration_minutes=675, stops=0,
        cabin="premium_economy", fare_basis="UA-PRE-SAVER", total_usd=1555.24,
        refundable=False, co2_kg=1192.3, aircraft="Boeing 777-200ER",
    )
    hotel = HotelOffer(
        offer_id="HT-2", hotel_id=2, name="Konan Garden Hotel", city="Tokyo",
        address="3-2-16 Konan", star_rating=3, distance_km_to_venue=0.56,
        nightly_rate_usd=189.96, nights=3, total_usd=569.88, refundable=True,
        breakfast_included=False,
    )
    return {
        "trip_ref": "TRIP-1",
        "traveller": TravellerProfile(
            employee_id=1, full_name="Mira Halvorsen",
            email="mira.halvorsen@nimbusrobotics.example",
            title="Staff Robotics Engineer", grade="IC5", home_iata="SFO",
            passport_country="United States", cost_center_id="CC-1",
            manager_email="elena.marchetti@nimbusrobotics.example",
        ),
        "request": TripRequest(
            trip_ref="TRIP-1", employee_email="mira.halvorsen@nimbusrobotics.example",
            purpose="QBR", origin_iata="SFO", destination_iata="HND",
            depart_date=date(2026, 10, 14), return_date=date(2026, 10, 17),
        ),
        "flights": FlightProposal(
            trip_ref="TRIP-1", outbound=leg,
            inbound=leg.model_copy(update={"direction": "return"}), total_usd=3110.48,
        ),
        "stay": StayProposal(trip_ref="TRIP-1", recommended=hotel, total_usd=569.88),
        "ground_usd": 8.40,
    }


def test_the_total_is_flights_plus_lodging_plus_ground():
    itinerary = graph.build_itinerary({**sample_state(), "budget": budget("approved")})
    assert itinerary.total_usd == 3688.76


def test_an_approved_budget_makes_the_itinerary_confirmed():
    itinerary = graph.build_itinerary({**sample_state(), "budget": budget("approved")})
    assert itinerary.status == "confirmed"


def test_an_unapproved_budget_leaves_the_itinerary_waiting():
    itinerary = graph.build_itinerary({**sample_state(), "budget": budget("needs_approval")})
    assert itinerary.status == "awaiting_approval"


def test_a_trip_with_no_budget_decision_is_not_reported_as_confirmed():
    assert graph.build_itinerary(sample_state()).status == "rejected"
