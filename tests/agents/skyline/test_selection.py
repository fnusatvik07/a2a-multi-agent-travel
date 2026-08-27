"""Skyline chooses a cabin, ranks fares, and refuses to trust the model blindly."""

from __future__ import annotations

from datetime import date

import pytest
from skyline_adk import agent, service

from atlastrip_core.models import FlightBrief


def brief(**overrides) -> FlightBrief:
    fields = {
        "trip_ref": "TRIP-1",
        "origin_iata": "SFO",
        "dest_iata": "HND",
        "depart_date": date(2026, 10, 14),
        "return_date": date(2026, 10, 17),
        "traveller_grade": "IC5",
    }
    fields.update(overrides)
    return FlightBrief(**fields)


def fare(fare_id: int, cabin: str, total: float, minutes: int = 675, stops: int = 0) -> dict:
    return {
        "id": fare_id,
        "carrier": "UA",
        "flight_no": "UA 837",
        "origin_iata": "SFO",
        "dest_iata": "HND",
        "depart_utc": "2026-10-14T17:55:00+00:00",
        "arrive_utc": "2026-10-15T05:10:00+00:00",
        "duration_minutes": minutes,
        "stops": stops,
        "cabin": cabin,
        "fare_basis": f"UA-{cabin[:3].upper()}-SAVER",
        "total_usd": total,
        "refundable": False,
        "co2_kg": 1192.3,
        "aircraft": "Boeing 777-200ER",
    }


def test_long_haul_takes_premium_economy_when_it_is_close_in_price():
    rows = [fare(1, "economy", 1000.0), fare(2, "premium_economy", 1600.0)]
    assert {row["cabin"] for row in service._trim(rows, brief())} == {"premium_economy"}


def test_long_haul_stays_in_economy_when_premium_is_not_worth_it():
    rows = [fare(1, "economy", 1000.0), fare(2, "premium_economy", 2400.0)]
    assert {row["cabin"] for row in service._trim(rows, brief())} == {"economy"}


def test_a_short_hop_never_upgrades():
    """The comfort argument only holds over distance."""
    rows = [
        fare(1, "economy", 300.0, minutes=330),
        fare(2, "premium_economy", 320.0, minutes=330),
    ]
    assert {row["cabin"] for row in service._trim(rows, brief())} == {"economy"}


def test_an_explicit_cabin_overrides_the_choice():
    rows = [fare(1, "economy", 1000.0), fare(2, "premium_economy", 1100.0)]
    trimmed = service._trim(rows, brief(cabin="economy"))
    assert {row["cabin"] for row in trimmed} == {"economy"}


def test_fares_are_ranked_cheapest_then_fewest_stops_then_shortest():
    rows = [
        fare(1, "economy", 900.0, stops=1),
        fare(2, "economy", 900.0, stops=0),
        fare(3, "economy", 800.0, stops=2),
    ]
    assert [row["id"] for row in service._trim(rows, brief())] == [3, 2, 1]


def test_the_models_choice_is_honoured_when_it_names_a_real_fare():
    candidates = {
        "outbound": [fare(1, "economy", 900.0), fare(2, "economy", 950.0)],
        "inbound": [fare(3, "economy", 900.0)],
    }
    proposal = service.assemble(
        brief(), candidates, outbound_offer_id="FL-2", inbound_offer_id="FL-3"
    )
    assert proposal.outbound.offer_id == "FL-2"


def test_an_invented_fare_falls_back_to_the_ranking():
    """A model must never be able to quote an itinerary that is not bookable."""
    candidates = {
        "outbound": [fare(1, "economy", 900.0), fare(2, "economy", 950.0)],
        "inbound": [fare(3, "economy", 900.0)],
    }
    proposal = service.assemble(
        brief(), candidates, outbound_offer_id="FL-9999", inbound_offer_id="FL-3"
    )
    assert proposal.outbound.offer_id == "FL-1"


def test_no_inventory_is_an_error_rather_than_an_empty_itinerary():
    with pytest.raises(LookupError):
        service.assemble(brief(), {"outbound": [], "inbound": []})


def test_the_total_is_the_two_legs_added_up():
    candidates = {"outbound": [fare(1, "economy", 900.0)], "inbound": [fare(2, "economy", 850.5)]}
    assert service.assemble(brief(), candidates).total_usd == 1750.5


@pytest.mark.parametrize(
    "reply",
    [
        '{"outbound_offer_id": "FL-1", "inbound_offer_id": "FL-2", "rationale": "cheapest"}',
        'Here you go:\n```json\n{"outbound_offer_id": "FL-1", '
        '"inbound_offer_id": "FL-2", "rationale": "cheapest"}\n```',
    ],
)
def test_the_models_json_is_found_however_it_is_wrapped(reply):
    selection = agent._parse(reply)
    assert selection.outbound_offer_id == "FL-1"
    assert selection.rationale == "cheapest"


@pytest.mark.parametrize("reply", ["", "I would take the United flight.", "{not json}"])
def test_an_unusable_reply_yields_an_empty_selection(reply):
    selection = agent._parse(reply)
    assert selection.outbound_offer_id is None
