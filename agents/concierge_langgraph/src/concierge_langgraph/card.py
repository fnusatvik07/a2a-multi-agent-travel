"""The Concierge's Agent Card.

Note that it looks like any other agent's card. Nothing on it says "this one
orchestrates the others". To a caller, the Concierge is simply an agent that
can plan a trip; that it does so by commissioning four other agents is an
implementation detail on the far side of the interface.
"""

from __future__ import annotations

from atlastrip_core.a2a_support import build_agent_card
from atlastrip_core.registry import CONCIERGE
from a2a.types import AgentCard, AgentSkill


DESCRIPTION = (
    "Plans a corporate trip end to end. Reads a request in plain English, "
    "commissions flights, lodging, a policy ruling and a budget authorisation "
    "from the specialists, renegotiates whatever policy rejects, and returns a "
    "single itinerary. Pauses in input-required when a human has to approve "
    "the spend."
)


def agent_card() -> AgentCard:
    return build_agent_card(
        CONCIERGE,
        description=DESCRIPTION,
        skills=[
            AgentSkill(
                id=CONCIERGE.skill_id,
                name="Plan a trip",
                description=(
                    "Describe the trip in plain English. Returns a complete "
                    "itinerary with flights, lodging, the policy findings and "
                    "the budget decision. If the spend needs sign-off the task "
                    "pauses; reply on the same task with approve or decline."
                ),
                tags=["orchestration", "travel", "itinerary"],
                examples=[
                    "Mira Halvorsen needs to be at the Kaisei QBR in Tokyo "
                    "from 14 to 17 October 2026.",
                    "approve",
                ],
                input_modes=["text", "data"],
                output_modes=["text", "data"],
            )
        ],
    )
