"""Ledger's Agent Card."""

from __future__ import annotations

from a2a.types import AgentCard, AgentSkill

from atlastrip_core.a2a_support import build_agent_card
from atlastrip_core.registry import LEDGER

DESCRIPTION = (
    "Authorises travel spend against a cost centre. Checks the live budget "
    "position, approves what it can, and interrupts the task in "
    "input-required when a human has to sign off. Writes the commitment to "
    "the ledger once authorised."
)


def agent_card() -> AgentCard:
    return build_agent_card(
        LEDGER,
        description=DESCRIPTION,
        skills=[
            AgentSkill(
                id=LEDGER.skill_id,
                name="Authorise spend",
                description=(
                    "Given a cost centre and a cost breakdown, return approved, "
                    "needs_approval or rejected with the budget position. When "
                    "the answer is needs_approval the task pauses in "
                    "input-required; send the approval token back on the same "
                    "task to resume it."
                ),
                tags=["finance", "budget", "approval", "human-in-the-loop"],
                examples=[
                    "Authorise 3,694 USD against CC-ROBOTICS-APAC for TRIP-2026-0042.",
                    "Here is the manager's approval token, please proceed.",
                ],
                input_modes=["text", "data"],
                output_modes=["text", "data"],
            )
        ],
    )
