"""Skyline's reasoning layer, built on Google ADK.

The ADK agent is given the inventory MCP server as a toolset, so it can look
around the timetable itself rather than being handed a fixed list. Its job is
to choose one outbound and one return flight from the shortlist and say why.

The choice comes back as JSON in the model's reply. ADK refuses to combine a
strict ``output_schema`` with tools, so rather than give up the tools we parse
the reply leniently and fall back to the deterministic ranking in ``service``
whenever the answer is missing, malformed or names a flight that does not
exist. A model is allowed to have an opinion here; it is not allowed to invent
an itinerary.
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Any

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.models import FlightBrief
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types


log = get_logger("skyline")

APP_NAME = "skyline"

INSTRUCTION = """\
You are Skyline, the flight desk of an autonomous corporate travel network.

You are given a shortlist of bookable fares for one round trip. Choose exactly
one outbound flight and one return flight from that shortlist.

Weigh, in this order:
  1. total fare,
  2. a departure that leaves the traveller usable time at the destination,
  3. non-stop over connecting,
  4. a refundable fare when the difference is small.

You may call search_flights to look at the wider timetable before deciding, but
you must choose from the shortlist you were given.

Do not comment on whether the traveller is allowed this cabin or this carrier.
That is Sentinel's ruling, not yours.

Reply with nothing but a JSON object:
{"outbound_offer_id": "FL-123", "inbound_offer_id": "FL-456",
 "rationale": "one or two sentences, naming the carrier and the fare"}
"""


@dataclass
class Selection:
    """What the model decided, once we have made sure it is usable."""

    outbound_offer_id: str | None = None
    inbound_offer_id: str | None = None
    rationale: str = ""


def build_agent() -> LlmAgent:
    """An ADK agent whose tools are the shared inventory MCP server."""
    return LlmAgent(
        name=APP_NAME,
        model=LiteLlm(model=f"openai/{settings().openai_model}"),
        instruction=INSTRUCTION,
        tools=[
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=settings().mcp_url
                ),
                tool_filter=["search_flights", "list_airports"],
            )
        ],
    )


async def choose(
    brief: FlightBrief, candidates: dict[str, list[dict[str, Any]]]
) -> Selection:
    """Ask the ADK agent to pick from the shortlist.

    Any failure at all, from a missing API key to a model that answers in
    prose, returns an empty ``Selection`` and lets the caller fall back.
    """
    if not settings().uses_llm:
        return Selection()

    try:
        return await _run(brief, candidates)
    except Exception as error:  # the network must survive a bad model turn
        log.warning("ADK selection unavailable, using the ranking instead: %s", error)
        return Selection()


async def _run(
    brief: FlightBrief, candidates: dict[str, list[dict[str, Any]]]
) -> Selection:
    agent = build_agent()
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=APP_NAME, agent=agent, session_service=session_service
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=brief.trip_ref
    )

    prompt = types.Content(
        role="user",
        parts=[types.Part(text=_prompt(brief, candidates))],
    )

    reply = ""
    async for event in runner.run_async(
        user_id=brief.trip_ref, session_id=session.id, new_message=prompt
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply = "".join(part.text or "" for part in event.content.parts)

    selection = _parse(reply)
    log.info(
        "ADK chose %s / %s",
        selection.outbound_offer_id or "(ranking)",
        selection.inbound_offer_id or "(ranking)",
    )
    return selection


def _prompt(brief: FlightBrief, candidates: dict[str, list[dict[str, Any]]]) -> str:
    return "\n".join(
        [
            f"Trip {brief.trip_ref}: {brief.origin_iata} to {brief.dest_iata}, "
            f"out {brief.depart_date}, back {brief.return_date}. "
            f"Traveller grade {brief.traveller_grade}.",
            "",
            "Outbound shortlist:",
            _table(candidates["outbound"]),
            "",
            "Return shortlist:",
            _table(candidates["inbound"]),
        ]
    )


def _table(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"  FL-{row['id']}  {row['flight_no']}  {row['cabin']}  "
        f"{row['fare_basis']}  ${row['total_usd']:,.2f}  "
        f"{row['duration_minutes']}min  {row['stops']} stops  "
        f"depart {row['depart_utc']}  "
        f"{'refundable' if row['refundable'] else 'non-refundable'}"
        for row in rows
    )


def _parse(reply: str) -> Selection:
    """Read the model's JSON out of whatever it wrapped the JSON in."""
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return Selection()
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Selection()
    return Selection(
        outbound_offer_id=payload.get("outbound_offer_id"),
        inbound_offer_id=payload.get("inbound_offer_id"),
        rationale=str(payload.get("rationale", "")).strip(),
    )
