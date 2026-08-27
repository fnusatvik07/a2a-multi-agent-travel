"""Sentinel's Agent Card."""

from __future__ import annotations

from atlastrip_core.a2a_support import build_agent_card
from atlastrip_core.registry import SENTINEL
from a2a.types import AgentCard, AgentSkill


DESCRIPTION = (
    "Rules on whether a trip may proceed. Evaluates the corporate travel "
    "policy and the entry rulebook against an assembled itinerary and returns "
    "findings, a compliance verdict and whether a manager has to sign it off."
)


def agent_card() -> AgentCard:
    return build_agent_card(
        SENTINEL,
        description=DESCRIPTION,
        skills=[
            AgentSkill(
                id=SENTINEL.skill_id,
                name="Screen a trip",
                description=(
                    "Given a traveller, their flights, their stay and the "
                    "booking date, return every policy finding with a severity, "
                    "the entry documentation requirement for that passport and "
                    "destination, and whether the trip is within policy."
                ),
                tags=["policy", "compliance", "visa", "rag"],
                examples=[
                    "Screen TRIP-2026-0042 against travel policy.",
                    "Does a US passport need a visa for Japan in October?",
                ],
                input_modes=["text", "data"],
                output_modes=["text", "data"],
            )
        ],
    )
