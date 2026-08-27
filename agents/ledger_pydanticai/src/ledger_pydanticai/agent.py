"""Ledger's reasoning layer, built on Pydantic AI.

Pydantic AI is here for the thing it does better than anything else on this
network: a typed answer. ``output_type=SpendOpinion`` means the model cannot
return prose where a decision was asked for, and the result arrives already
validated.

Note what the agent is and is not allowed to do. It reads the live budget
position through the shared MCP server and writes the reasoning a human will
read. It does not move money: ``service.assess`` has already decided, and this
opinion is only allowed to make the outcome stricter, never looser. An
optimistic model cannot spend anything.
"""

from __future__ import annotations

from typing import Literal

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.models import BudgetVerdict, SpendRequest
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel


log = get_logger("ledger")

INSTRUCTIONS = """\
You are Ledger, the budget desk of an autonomous corporate travel network.

You are given a spend request and the decision the ledger has already reached.
Look up the cost centre's live position with get_cost_center_budget, then write
the reasoning that goes to the traveller and their manager.

State the amount, what remains in the quarter, and what has to happen next in
one or two sentences. Speak plainly; a manager reads this on their phone.

You may raise a concern the ledger did not, by setting concern. You may not
overturn the decision.
"""


class SpendOpinion(BaseModel):
    """The model's typed contribution to the decision."""

    reason: str = Field(
        description="One or two sentences for the traveller and their manager."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="high", description="How clear cut this decision is."
    )
    concern: str = Field(
        default="",
        description="Anything the ledger's arithmetic would not have caught.",
    )


def build_agent() -> Agent[None, SpendOpinion]:
    return Agent(
        OpenAIChatModel(settings().openai_model),
        output_type=SpendOpinion,
        instructions=INSTRUCTIONS,
        toolsets=[MCPToolset(settings().mcp_url)],
    )


async def explain(
    request: SpendRequest, verdict: BudgetVerdict
) -> SpendOpinion | None:
    """Ask Pydantic AI to write the reasoning. ``None`` if it cannot."""
    if not settings().uses_llm:
        return None
    try:
        agent = build_agent()
        result = await agent.run(_prompt(request, verdict))
        log.info("Pydantic AI opinion: confidence=%s", result.output.confidence)
        return result.output
    except Exception as error:  # the decision stands with or without the prose
        log.warning("Pydantic AI opinion unavailable: %s", error)
        return None


def _prompt(request: SpendRequest, verdict: BudgetVerdict) -> str:
    return "\n".join(
        [
            f"Trip {request.trip_ref} for {request.employee_email}.",
            f"Cost centre: {request.cost_center_id}.",
            f"Flights ${request.flights_usd:,.2f}, "
            f"lodging ${request.lodging_usd:,.2f}, "
            f"ground ${request.ground_usd:,.2f}. "
            f"Total ${request.total_usd:,.2f}.",
            f"Policy says manager approval is "
            f"{'required' if request.requires_manager_approval else 'not required'}.",
            "",
            f"The ledger has decided: {verdict.decision}.",
            f"Remaining before this trip: ${verdict.remaining_before_usd:,.2f}.",
            f"Remaining after: ${verdict.remaining_after_usd:,.2f}.",
        ]
    )
