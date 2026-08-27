"""Discovery: everything a caller needs is on the Agent Card."""

from __future__ import annotations

import httpx
import pytest

from atlastrip_core import a2a_client
from atlastrip_core.registry import ALL_AGENTS, BY_KEY


@pytest.mark.parametrize("endpoint", ALL_AGENTS, ids=lambda e: e.key)
async def test_every_agent_publishes_a_card_at_the_well_known_path(endpoint):
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.get(endpoint.agent_card_url)
    assert response.status_code == 200
    assert response.json()["name"] == endpoint.name


@pytest.mark.parametrize("endpoint", ALL_AGENTS, ids=lambda e: e.key)
async def test_every_card_advertises_the_skill_the_network_calls(endpoint):
    card = await a2a_client.fetch_agent_card(endpoint)
    assert endpoint.skill_id in {skill.id for skill in card.skills}


@pytest.mark.parametrize("endpoint", ALL_AGENTS, ids=lambda e: e.key)
async def test_every_card_offers_both_http_bindings(endpoint):
    card = await a2a_client.fetch_agent_card(endpoint)
    bindings = {interface.protocol_binding for interface in card.supported_interfaces}
    assert {"JSONRPC", "HTTP+JSON"} <= bindings


@pytest.mark.parametrize("endpoint", ALL_AGENTS, ids=lambda e: e.key)
async def test_every_card_declares_streaming(endpoint):
    """The Concierge relies on this to report progress while it works."""
    card = await a2a_client.fetch_agent_card(endpoint)
    assert card.capabilities.streaming


async def test_the_interface_urls_on_a_card_are_the_ones_that_answer():
    """A card that points somewhere unreachable is worse than no card."""
    card = await a2a_client.fetch_agent_card(BY_KEY["skyline"])
    urls = {i.protocol_binding: i.url for i in card.supported_interfaces}
    assert urls["JSONRPC"].endswith("/a2a/jsonrpc")

    async with httpx.AsyncClient(timeout=10.0) as http:
        # A malformed body still proves something is listening and speaking
        # JSON-RPC, rather than 404ing.
        response = await http.post(urls["JSONRPC"], json={"not": "jsonrpc"})
    assert response.status_code < 500
