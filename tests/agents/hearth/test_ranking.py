"""Hearth's judgement, and the guard rails around the crew's answer."""

from __future__ import annotations

from datetime import date

import pytest

from atlastrip_core.models import StayBrief
from hearth_crewai import service


def brief(**overrides) -> StayBrief:
    fields = {
        "trip_ref": "TRIP-1",
        "city": "Tokyo",
        "check_in": date(2026, 10, 14),
        "check_out": date(2026, 10, 17),
        "venue_id": "KAISEI-HQ",
        "nightly_cap_usd": 280.0,
    }
    fields.update(overrides)
    return StayBrief(**fields)


def hotel(hotel_id: int, name: str, rate: float, km: float, stars: int, amenities=None) -> dict:
    return {
        "hotel_id": hotel_id,
        "name": name,
        "city": "Tokyo",
        "country": "Japan",
        "address": "somewhere",
        "star_rating": stars,
        "corporate_code": "NIMBUS-JP",
        "amenities": amenities if amenities is not None else ["wifi", "desk"],
        "nightly_rate_usd": rate,
        "distance_km_to_venue": km,
        "refundable": True,
        "breakfast_included": False,
        "rooms_available": 4,
    }


def test_proximity_outweighs_a_modest_price_difference():
    """This is the judgement call the whole demo turns on: Hearth will pay a
    little more to put the traveller next to the customer's front door."""
    ranked = service.rank(
        [
            hotel(1, "Near and dearer", 298.33, 0.21, 4),
            hotel(2, "Further and cheaper", 189.96, 0.56, 3),
        ]
    )
    assert ranked[0]["name"] == "Near and dearer"


def test_proximity_does_not_outweigh_an_absurd_price_difference():
    ranked = service.rank(
        [
            hotel(1, "Near and absurd", 900.0, 0.21, 5),
            hotel(2, "Further and sane", 150.0, 0.60, 4),
        ]
    )
    assert ranked[0]["name"] == "Further and sane"


def test_a_single_candidate_ranks_without_dividing_by_zero():
    """Normalising over one row must not blow up on an empty range."""
    assert len(service.rank([hotel(1, "Only option", 200.0, 1.0, 3)])) == 1


def test_rooms_without_a_desk_are_not_offered_to_a_business_traveller():
    assert not service._has_required_amenities(
        hotel(1, "Capsule", 60.0, 0.1, 2, amenities=["wifi"])
    )
    assert service._has_required_amenities(hotel(2, "Fine", 200.0, 0.1, 3))


def test_the_crews_choice_is_honoured_when_it_names_a_real_hotel():
    candidates = [hotel(1, "First", 250.0, 0.2, 4), hotel(2, "Second", 200.0, 0.4, 3)]
    assert service.assemble(brief(), candidates, offer_id="HT-2").recommended.name == "Second"


def test_an_invented_hotel_falls_back_to_the_ranking():
    candidates = [hotel(1, "First", 250.0, 0.2, 4)]
    assert service.assemble(brief(), candidates, offer_id="HT-404").recommended.name == "First"


def test_the_total_multiplies_the_nightly_rate_by_the_nights():
    candidates = [hotel(1, "First", 200.0, 0.2, 4)]
    proposal = service.assemble(brief(), candidates)
    assert proposal.recommended.nights == 3
    assert proposal.total_usd == 600.0


def test_an_empty_shortlist_is_an_error_rather_than_a_silent_no_hotel():
    with pytest.raises(LookupError):
        service.assemble(brief(), [])


def test_alternatives_never_repeat_the_recommendation():
    candidates = [hotel(i, f"H{i}", 200.0 + i, 0.2 * i, 4) for i in range(1, 5)]
    proposal = service.assemble(brief(), candidates)
    names = {alternative.name for alternative in proposal.alternatives}
    assert proposal.recommended.name not in names
