"""Sentinel's screening, without the model.

Resolves the one fact the rules engine cannot look up for itself (which
country the destination airport is in), then runs the policy book over the
trip. Used directly in deterministic mode, and as the binding ruling in LLM
mode.
"""

from __future__ import annotations

from atlastrip_core.mcp_http import MCPClient
from atlastrip_core.models import ComplianceVerdict, ScreeningRequest

from . import rules

_COUNTRY_BY_IATA: dict[str, str] = {}
"""Airports do not change while the process is alive.

Fetched once rather than on every screening: an MCP session is three round
trips, and opening one per request put avoidable load on the shared inventory
server for an answer that is always the same."""


async def _airport_countries() -> dict[str, str]:
    if not _COUNTRY_BY_IATA:
        async with MCPClient() as mcp:
            airports = await mcp.call("list_airports")
        _COUNTRY_BY_IATA.update(
            {airport["iata"]: airport["country"] for airport in airports}
        )
    return _COUNTRY_BY_IATA


async def destination_country(request: ScreeningRequest) -> str:
    """Which country the traveller is entering, from the destination airport."""
    countries = await _airport_countries()
    return countries.get(request.request.destination_iata.upper(), "Unknown")


async def screen(request: ScreeningRequest) -> ComplianceVerdict:
    """Rule on a trip. This is the whole job in deterministic mode."""
    return rules.evaluate(request, await destination_country(request))
