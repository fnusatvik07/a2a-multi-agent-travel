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


async def destination_country(request: ScreeningRequest) -> str:
    """Which country the traveller is entering, from the destination airport."""
    async with MCPClient() as mcp:
        airports = await mcp.call("list_airports")
    wanted = request.request.destination_iata.upper()
    for airport in airports:
        if airport["iata"] == wanted:
            return airport["country"]
    return "Unknown"


async def screen(request: ScreeningRequest) -> ComplianceVerdict:
    """Rule on a trip. This is the whole job in deterministic mode."""
    return rules.evaluate(request, await destination_country(request))
