"""The shared tool surface every specialist reads."""

from __future__ import annotations

import pytest

from atlastrip_core.mcp_http import MCPClient

EXPECTED_TOOLS = {
    "search_flights",
    "list_airports",
    "search_hotels",
    "get_ground_transport",
    "lookup_employee",
    "lookup_venue",
    "get_cost_center_budget",
    "record_commitment",
}


@pytest.fixture
async def mcp():
    async with MCPClient() as client:
        yield client


async def test_the_server_advertises_the_whole_tool_surface(mcp):
    assert {tool["name"] for tool in await mcp.list_tools()} == EXPECTED_TOOLS


async def test_every_tool_carries_a_description_a_model_can_act_on(mcp):
    for tool in await mcp.list_tools():
        assert tool.get("description"), f"{tool['name']} has no description"


async def test_flights_are_returned_for_the_local_departure_date(mcp):
    """A date means the date on the departure board, not a UTC window."""
    rows = await mcp.call(
        "search_flights",
        origin_iata="SFO",
        dest_iata="HND",
        depart_date="2026-10-14",
        limit=50,
    )
    assert rows
    # SFO is UTC-7 in October, so a local 14 October departure is 14 October
    # after 07:00 UTC, or 15 October before 07:00 UTC.
    for row in rows:
        assert row["depart_utc"][:10] in {"2026-10-14", "2026-10-15"}


async def test_flights_come_back_cheapest_first(mcp):
    rows = await mcp.call(
        "search_flights", origin_iata="SFO", dest_iata="HND",
        depart_date="2026-10-14", limit=10,
    )
    fares = [row["total_usd"] for row in rows]
    assert fares == sorted(fares)


async def test_the_cabin_filter_is_honoured(mcp):
    rows = await mcp.call(
        "search_flights", origin_iata="SFO", dest_iata="HND",
        depart_date="2026-10-14", cabin="business", limit=10,
    )
    assert rows and {row["cabin"] for row in rows} == {"business"}


async def test_the_carrier_filter_is_honoured(mcp):
    rows = await mcp.call(
        "search_flights", origin_iata="SFO", dest_iata="HND",
        depart_date="2026-10-14", preferred_carriers=["NH"], limit=10,
    )
    assert rows and {row["carrier"] for row in rows} == {"NH"}


async def test_a_route_with_no_inventory_returns_nothing_rather_than_failing(mcp):
    assert await mcp.call(
        "search_flights", origin_iata="SYD", dest_iata="FRA",
        depart_date="2026-10-14",
    ) == []


async def test_hotels_are_measured_against_the_venue(mcp):
    rows = await mcp.call(
        "search_hotels", city="Tokyo", check_in="2026-10-14",
        check_out="2026-10-17", venue_id="KAISEI-HQ", limit=5,
    )
    assert rows
    distances = [row["distance_km_to_venue"] for row in rows]
    assert all(distance is not None for distance in distances)
    assert distances == sorted(distances), "nearest first when a venue is given"


async def test_a_nightly_cap_excludes_the_rooms_above_it(mcp):
    rows = await mcp.call(
        "search_hotels", city="Tokyo", check_in="2026-10-14",
        check_out="2026-10-17", max_nightly_rate=200.0, limit=20,
    )
    assert rows
    assert all(float(row["nightly_rate_usd"]) <= 200.0 for row in rows)


async def test_a_stay_is_priced_for_the_nights_not_the_days(mcp):
    rows = await mcp.call(
        "search_hotels", city="Tokyo", check_in="2026-10-14",
        check_out="2026-10-17", limit=1,
    )
    row = rows[0]
    assert row["nights"] == 3
    assert row["total_usd"] == pytest.approx(
        float(row["nightly_rate_usd"]) * 3, abs=0.01
    )


async def test_an_employee_lookup_returns_what_policy_needs(mcp):
    record = await mcp.call_one(
        "lookup_employee", email="mira.halvorsen@nimbusrobotics.example"
    )
    assert record["grade"] == "IC5"
    assert record["passport_country"] == "United States"
    assert record["cost_center_id"] == "CC-ROBOTICS-APAC"


async def test_an_unknown_employee_is_absent_rather_than_invented(mcp):
    assert await mcp.call_one("lookup_employee", email="nobody@example.com") is None


async def test_the_budget_position_adds_up(mcp):
    position = await mcp.call_one(
        "get_cost_center_budget", cost_center_id="CC-ROBOTICS-APAC"
    )
    assert position["remaining_usd"] == pytest.approx(
        position["quarterly_budget_usd"] - position["committed_usd"], abs=0.01
    )
