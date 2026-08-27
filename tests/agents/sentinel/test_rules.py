"""Sentinel's rulings.

These run against the policy clauses that actually ship in
``data/seed/policies.json``, so a change to the policy data that breaks a rule
fails here rather than in front of a traveller.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from atlastrip_core.models import (
    FlightOffer,
    FlightProposal,
    HotelOffer,
    ScreeningRequest,
    StayProposal,
    TravellerProfile,
    TripRequest,
)
from sentinel_llamaindex import rules


BOOKED_ON = date(2026, 8, 27)
DEPARTS_ON = date(2026, 10, 14)
RETURNS_ON = date(2026, 10, 17)


def traveller(grade: str = "IC5", passport: str = "United States") -> TravellerProfile:
    return TravellerProfile(
        employee_id=1,
        full_name="Mira Halvorsen",
        email="mira.halvorsen@nimbusrobotics.example",
        title="Staff Robotics Engineer",
        grade=grade,
        home_iata="SFO",
        passport_country=passport,
        cost_center_id="CC-ROBOTICS-APAC",
        manager_email="elena.marchetti@nimbusrobotics.example",
    )


def leg(direction: str, cabin: str, total: float, carrier: str = "UA", minutes: int = 675,
        refundable: bool = False, co2: float = 1192.3) -> FlightOffer:
    return FlightOffer(
        offer_id=f"FL-{direction}",
        direction=direction,
        carrier=carrier,
        flight_no=f"{carrier} 837",
        origin_iata="SFO",
        dest_iata="HND",
        depart_utc=datetime(2026, 10, 14, 17, 55),
        arrive_utc=datetime(2026, 10, 15, 5, 10),
        duration_minutes=minutes,
        stops=0,
        cabin=cabin,
        fare_basis="UA-PRE-SAVER",
        total_usd=total,
        refundable=refundable,
        co2_kg=co2,
        aircraft="Boeing 777-200ER",
    )


def flights(cabin: str = "premium_economy", total_each: float = 1555.24, **kwargs) -> FlightProposal:
    outbound = leg("outbound", cabin, total_each, **kwargs)
    inbound = leg("return", cabin, total_each, **kwargs)
    return FlightProposal(
        trip_ref="TRIP-1", outbound=outbound, inbound=inbound,
        total_usd=round(total_each * 2, 2),
    )


def stay(nightly: float = 189.96, nights: int = 3) -> StayProposal:
    hotel = HotelOffer(
        offer_id="HT-2", hotel_id=2, name="Konan Garden Hotel", city="Tokyo",
        address="3-2-16 Konan", star_rating=3, distance_km_to_venue=0.56,
        nightly_rate_usd=nightly, nights=nights,
        total_usd=round(nightly * nights, 2), refundable=True,
        breakfast_included=False, corporate_code="NIMBUS-JP",
    )
    return StayProposal(trip_ref="TRIP-1", recommended=hotel, total_usd=hotel.total_usd)


def screening(**overrides) -> ScreeningRequest:
    fields = {
        "trip_ref": "TRIP-1",
        "traveller": traveller(),
        "request": TripRequest(
            trip_ref="TRIP-1",
            employee_email="mira.halvorsen@nimbusrobotics.example",
            purpose="QBR",
            origin_iata="SFO",
            destination_iata="HND",
            depart_date=DEPARTS_ON,
            return_date=RETURNS_ON,
            venue_id="KAISEI-HQ",
        ),
        "flights": flights(),
        "stay": stay(),
        "ground_usd": 8.40,
        "as_of": BOOKED_ON,
    }
    fields.update(overrides)
    return ScreeningRequest(**fields)


def findings_for(verdict, clause_id: str):
    return [f for f in verdict.findings if f.clause_id == clause_id]


# -- the shipped scenario ---------------------------------------------------


def test_the_reference_trip_is_within_policy_but_needs_sign_off():
    verdict = rules.evaluate(screening(), "Japan")
    assert verdict.compliant
    # TRV-005: it is over the auto-approval threshold.
    assert verdict.requires_manager_approval


def test_a_hotel_over_the_city_cap_is_a_violation():
    verdict = rules.evaluate(screening(stay=stay(nightly=298.33)), "Japan")
    breach = findings_for(verdict, "TRV-003")
    assert breach and breach[0].severity == "violation"
    assert breach[0].requires_approval
    assert not verdict.compliant


def test_the_violation_states_the_cap_so_the_caller_can_act_on_it():
    """The Concierge reads the cap back out of this text when it renegotiates,
    which is the only reason it does not need its own copy of the policy."""
    verdict = rules.evaluate(screening(stay=stay(nightly=298.33)), "Japan")
    assert "cap of $280.00" in findings_for(verdict, "TRV-003")[0].detail


def test_a_hotel_at_the_cap_exactly_is_allowed():
    verdict = rules.evaluate(screening(stay=stay(nightly=280.00)), "Japan")
    assert not findings_for(verdict, "TRV-003")


# -- cabin entitlement ------------------------------------------------------


def test_business_class_for_an_ic5_is_a_violation():
    verdict = rules.evaluate(screening(flights=flights(cabin="business")), "Japan")
    breach = findings_for(verdict, "TRV-001")
    assert breach and all(f.severity == "violation" for f in breach)


def test_business_class_for_a_director_is_fine():
    verdict = rules.evaluate(
        screening(traveller=traveller(grade="M3"), flights=flights(cabin="business")),
        "Japan",
    )
    assert not [f for f in findings_for(verdict, "TRV-001") if f.severity == "violation"]


def test_travelling_below_entitlement_is_noted_but_not_a_violation():
    verdict = rules.evaluate(screening(flights=flights(cabin="economy")), "Japan")
    breach = findings_for(verdict, "TRV-001")
    assert breach and all(f.severity == "info" for f in breach)


def test_premium_economy_on_a_short_hop_is_a_violation_for_any_grade():
    """The entitlement is earned by the flight time, not by the grade alone."""
    verdict = rules.evaluate(
        screening(flights=flights(cabin="premium_economy", minutes=330)), "Japan"
    )
    assert [f for f in findings_for(verdict, "TRV-001") if f.severity == "violation"]


# -- the other clauses ------------------------------------------------------


def test_an_unlisted_carrier_is_a_warning_not_a_block():
    verdict = rules.evaluate(screening(flights=flights(carrier="ZG")), "Japan")
    breach = findings_for(verdict, "TRV-002")
    assert breach and breach[0].severity == "warning"
    assert verdict.compliant


def test_booking_inside_the_advance_purchase_window_is_a_violation():
    verdict = rules.evaluate(screening(as_of=date(2026, 10, 8)), "Japan")
    assert findings_for(verdict, "TRV-004")[0].severity == "violation"


def test_a_cheap_trip_clears_the_threshold_without_a_manager():
    small = flights(total_each=300.0)
    verdict = rules.evaluate(
        screening(flights=small, stay=stay(nightly=100.0, nights=2)), "Japan"
    )
    assert not findings_for(verdict, "TRV-005")
    assert not verdict.requires_manager_approval


def test_ground_transport_over_the_cap_is_a_violation():
    verdict = rules.evaluate(screening(ground_usd=400.0), "Japan")
    assert findings_for(verdict, "TRV-007")[0].severity == "violation"


def test_emissions_over_the_ceiling_are_flagged():
    verdict = rules.evaluate(screening(flights=flights(co2=2000.0)), "Japan")
    assert findings_for(verdict, "TRV-008")[0].severity == "warning"


def test_a_non_refundable_fare_booked_at_the_last_minute_is_flagged():
    verdict = rules.evaluate(screening(as_of=date(2026, 10, 10)), "Japan")
    assert findings_for(verdict, "TRV-006")[0].severity == "warning"


# -- entry rules ------------------------------------------------------------


def test_a_us_passport_needs_no_visa_for_japan():
    verdict = rules.evaluate(screening(), "Japan")
    assert verdict.visa is not None
    assert verdict.visa.requirement == "visa_free"
    assert findings_for(verdict, "TRV-010")[0].severity == "info"


def test_a_visa_that_cannot_be_obtained_in_time_blocks_the_trip():
    """An Indian passport needs 30 days for the United States; this trip has 6."""
    request = screening(
        traveller=traveller(passport="India"), as_of=date(2026, 10, 8)
    )
    verdict = rules.evaluate(request, "United States")
    assert findings_for(verdict, "TRV-010")[0].severity == "violation"
    assert not verdict.compliant


def test_an_unknown_passport_and_destination_pair_is_escalated_not_assumed():
    verdict = rules.evaluate(
        screening(traveller=traveller(passport="Iceland")), "Japan"
    )
    finding = findings_for(verdict, "TRV-010")[0]
    assert finding.severity == "warning"
    assert finding.requires_approval


# -- the summary ------------------------------------------------------------


def test_the_summary_leads_with_violations_when_there_are_any():
    verdict = rules.evaluate(screening(stay=stay(nightly=298.33)), "Japan")
    assert verdict.summary.startswith("1 policy violation")


def test_the_summary_says_so_when_nothing_is_wrong():
    small = flights(total_each=300.0)
    verdict = rules.evaluate(
        screening(flights=small, stay=stay(nightly=100.0, nights=2)), "Japan"
    )
    assert verdict.summary == "Fully within policy."
