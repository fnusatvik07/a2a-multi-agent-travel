"""Skyline's Agent Card: what it will do, and where to reach it."""

from __future__ import annotations

from atlastrip_core.a2a_support import build_agent_card
from atlastrip_core.registry import SKYLINE
from a2a.types import AgentCard, AgentSkill


DESCRIPTION = (
    "Sources and ranks air travel for a round trip. Reads live fare inventory "
    "and returns one recommended outbound and return flight with alternatives. "
    "Does not rule on policy; ask Sentinel for that."
)


def agent_card() -> AgentCard:
    return build_agent_card(
        SKYLINE,
        description=DESCRIPTION,
        skills=[
            AgentSkill(
                id=SKYLINE.skill_id,
                name="Source flights",
                description=(
                    "Given a city pair, dates and the traveller's grade, return "
                    "a recommended round trip with fares, cabins, stop counts, "
                    "modelled emissions and up to four alternatives."
                ),
                tags=["air", "sourcing", "pricing"],
                examples=[
                    "Find flights SFO to HND departing 2026-10-14, back 2026-10-17.",
                    "Cheapest non-stop premium economy to Tokyo for an IC5.",
                ],
                input_modes=["text", "data"],
                output_modes=["text", "data"],
            )
        ],
    )
