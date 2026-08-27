"""Hearth's reasoning layer, built on CrewAI.

Where the other agents are a single model with tools, Hearth is a small crew,
because that is what CrewAI is for. Two roles work the problem in sequence:

  Scout       reads the shortlist and the surrounding inventory and describes
              what is actually on offer near the venue.
  Negotiator  makes the call, weighing the corporate rate and the nightly cap
              against how far the traveller would have to walk.

The Negotiator's task declares ``output_pydantic``, so CrewAI validates the
crew's answer into a typed object before we ever see it. If the crew cannot
run, or picks a hotel that is not on the shortlist, ``service`` falls back to
its own ranking.
"""

from __future__ import annotations

import asyncio
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import MCPServerAdapter
from pydantic import BaseModel, Field

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.models import StayBrief

log = get_logger("hearth")


class StaySelection(BaseModel):
    """The crew's answer, validated by CrewAI before it reaches us."""

    offer_id: str = Field(description="The chosen hotel, e.g. HT-1.")
    rationale: str = Field(
        description="One or two sentences on why this hotel over the others."
    )
    cap_exceeded: bool = Field(
        default=False,
        description="True when the chosen nightly rate is above the stated cap.",
    )


def _llm() -> LLM:
    return LLM(model=f"openai/{settings().openai_model}", temperature=0.2)


def build_crew(tools: list[Any]) -> Crew:
    scout = Agent(
        role="Lodging Scout",
        goal=(
            "Describe what is genuinely available near the traveller's meeting "
            "venue, including how far each option is and what it costs."
        ),
        backstory=(
            "You have booked corporate stays in this city for years. You know "
            "that a cheap room across town costs the traveller their evening, "
            "and you say so plainly."
        ),
        llm=_llm(),
        tools=tools,
        allow_delegation=False,
        verbose=False,
    )
    negotiator = Agent(
        role="Rate Negotiator",
        goal=(
            "Choose the single hotel that gives the company the best value, "
            "using the corporate rate wherever one exists."
        ),
        backstory=(
            "You hold the corporate rate agreements. You will go a little over "
            "a nightly cap when proximity clearly justifies it, and you always "
            "say when you have done so, because someone else has to sign it off."
        ),
        llm=_llm(),
        tools=tools,
        allow_delegation=False,
        verbose=False,
    )

    survey = Task(
        description=(
            "{brief}\n\nShortlist:\n{shortlist}\n\n"
            "Summarise what is on offer. For each option give the distance to "
            "the venue, the nightly rate, the star rating and whether a "
            "corporate rate applies. Do not choose yet."
        ),
        expected_output="A short prose comparison of the shortlisted hotels.",
        agent=scout,
    )
    decide = Task(
        description=(
            "Choose one hotel from the shortlist for this stay.\n\n{brief}\n\n"
            "Shortlist:\n{shortlist}\n\n"
            "Prefer a property within walking distance of the venue. Prefer a "
            "corporate rate. If the nightly rate you choose is above the cap "
            "you were given, choose it anyway when proximity justifies it, but "
            "set cap_exceeded so it can be reviewed."
        ),
        expected_output="The chosen offer id with a short justification.",
        agent=negotiator,
        context=[survey],
        output_pydantic=StaySelection,
    )

    return Crew(
        agents=[scout, negotiator],
        tasks=[survey, decide],
        process=Process.sequential,
        verbose=False,
    )


async def choose(
    brief: StayBrief, candidates: list[dict[str, Any]]
) -> StaySelection | None:
    """Run the crew. Returns ``None`` whenever its answer cannot be trusted."""
    if not settings().uses_llm:
        return None
    try:
        return await asyncio.to_thread(_run_crew, brief, candidates)
    except Exception as error:  # the network must survive a bad crew run
        log.warning("CrewAI selection unavailable, using the ranking instead: %s", error)
        return None


def _run_crew(
    brief: StayBrief, candidates: list[dict[str, Any]]
) -> StaySelection | None:
    """CrewAI is synchronous, so this runs on a worker thread."""
    # The crew reads the same MCP server the rest of the network reads, through
    # CrewAI's own adapter. The tools are identical; only the client differs.
    with MCPServerAdapter(
        {"url": settings().mcp_url, "transport": "streamable-http"}
    ) as mcp_tools:
        tools = [tool for tool in mcp_tools if tool.name in {"search_hotels", "lookup_venue"}]
        crew = build_crew(tools)
        result = crew.kickoff(
            inputs={
                "brief": _describe(brief),
                "shortlist": _table(candidates),
            }
        )

    selection = getattr(result, "pydantic", None)
    if isinstance(selection, StaySelection):
        log.info("CrewAI chose %s", selection.offer_id)
        return selection
    return None


def _describe(brief: StayBrief) -> str:
    cap = (
        f"Nightly cap guidance: ${brief.nightly_cap_usd:,.2f}."
        if brief.nightly_cap_usd
        else "No nightly cap was given."
    )
    if brief.enforce_cap:
        cap += " On this request the cap is a hard limit and must not be exceeded."
    return (
        f"Trip {brief.trip_ref}. {brief.city}, checking in {brief.check_in}, "
        f"out {brief.check_out}. Meeting venue: {brief.venue_id or 'not specified'}. "
        f"{cap}"
    )


def _table(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"  HT-{row['hotel_id']}  {row['name']}  {row['star_rating']} star  "
        f"${float(row['nightly_rate_usd']):,.2f}/night  "
        f"{float(row.get('distance_km_to_venue') or 0):.2f} km from venue  "
        f"corporate rate: {row.get('corporate_code') or 'none'}  "
        f"amenities: {', '.join(row.get('amenities') or [])}"
        for row in rows
    )
