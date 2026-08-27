"""Hearth's Agent Card."""

from __future__ import annotations

from atlastrip_core.a2a_support import build_agent_card
from atlastrip_core.registry import HEARTH
from a2a.types import AgentCard, AgentSkill


DESCRIPTION = (
    "Finds somewhere to stay near where the traveller has to be. Weighs "
    "proximity to the meeting venue against nightly rate and quality, and "
    "applies corporate rate agreements. Treats a nightly cap as guidance "
    "unless told to enforce it."
)


def agent_card() -> AgentCard:
    return build_agent_card(
        HEARTH,
        description=DESCRIPTION,
        skills=[
            AgentSkill(
                id=HEARTH.skill_id,
                name="Source a stay",
                description=(
                    "Given a city, dates and optionally a meeting venue, return "
                    "one recommended hotel with its nightly rate, distance to "
                    "the venue and corporate code, plus alternatives. Set "
                    "enforce_cap on the brief to make the nightly cap a hard "
                    "constraint."
                ),
                tags=["lodging", "sourcing", "corporate-rates"],
                examples=[
                    "Three nights in Tokyo near KAISEI-HQ from 2026-10-14.",
                    "Re-shortlist that stay under 280 USD a night.",
                ],
                input_modes=["text", "data"],
                output_modes=["text", "data"],
            )
        ],
    )
