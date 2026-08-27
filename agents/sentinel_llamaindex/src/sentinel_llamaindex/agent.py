"""Sentinel's reasoning layer, built on LlamaIndex.

Sentinel is the one agent on the network whose subject matter is prose. The
travel policy is a document, not a table, so LlamaIndex is used the way it is
meant to be used: the clause text is embedded into a vector index, and a
``FunctionAgent`` retrieves the passages that bear on this particular trip.

What the agent produces is an explanation, not a ruling. The ruling comes from
``rules.py``, which evaluates the structured half of each clause in ordinary
Python. A traveller should never be stopped, or waved through, because a model
paraphrased a paragraph.
"""

from __future__ import annotations

from functools import lru_cache

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.models import ComplianceVerdict, ScreeningRequest

from . import rules

log = get_logger("sentinel")

TOP_K = 4

INSTRUCTION = """\
You are Sentinel, the travel policy desk of an autonomous corporate travel
network. You have already been given the binding ruling on this trip. Your job
is to explain it to the traveller.

Use search_policy to pull the wording of the clauses that matter here, then
write a short briefing that:
  - says plainly whether the trip can proceed as booked,
  - explains each violation in the policy's own terms,
  - says exactly what the traveller or their manager has to do next.

Cite clause ids. Do not invent clauses, and do not soften or overturn the
ruling you were given.
"""


class PolicyBriefing(BaseModel):
    """The explanation Sentinel returns alongside the binding findings."""

    summary: str = Field(description="Two or three sentences for the traveller.")
    cited_clauses: list[str] = Field(
        default_factory=list, description="Clause ids the briefing relies on."
    )
    next_step: str = Field(
        default="", description="The single next action, or empty if none."
    )


@lru_cache(maxsize=1)
def policy_index() -> VectorStoreIndex:
    """Embed the policy book once per process.

    Ten clauses is a small index, which is the point: it is small enough to
    read, and large enough that retrieval genuinely beats stuffing the whole
    book into every prompt.
    """
    Settings.llm = OpenAI(model=settings().openai_model)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    docs = [
        Document(
            text=f"{clause['clause_id']}: {clause['title']}\n\n{clause['text']}",
            metadata={
                "clause_id": clause["clause_id"],
                "title": clause["title"],
                "category": clause["category"],
                "hard_rule": clause["hard_rule"],
            },
        )
        for clause in rules.load_clauses()
    ]
    log.info("indexing %d policy clauses", len(docs))
    return VectorStoreIndex.from_documents(docs)


def search_policy(question: str) -> str:
    """Retrieve the travel policy clauses most relevant to a question."""
    nodes = policy_index().as_retriever(similarity_top_k=TOP_K).retrieve(question)
    if not nodes:
        return "No policy clause matched that question."
    return "\n\n---\n\n".join(node.get_content() for node in nodes)


def build_agent() -> FunctionAgent:
    return FunctionAgent(
        name="sentinel",
        description="Explains corporate travel policy rulings.",
        system_prompt=INSTRUCTION,
        tools=[
            FunctionTool.from_defaults(
                fn=search_policy,
                name="search_policy",
                description=(
                    "Search the corporate travel policy. Pass a question in "
                    "plain English and receive the full text of the clauses "
                    "that bear on it."
                ),
            )
        ],
        llm=OpenAI(model=settings().openai_model),
        output_cls=PolicyBriefing,
    )


async def explain(
    request: ScreeningRequest, verdict: ComplianceVerdict
) -> PolicyBriefing | None:
    """Ask LlamaIndex to write the briefing. ``None`` if it cannot."""
    if not settings().uses_llm:
        return None
    try:
        agent = build_agent()
        response = await agent.run(user_msg=_prompt(request, verdict))
        briefing = getattr(response, "structured_response", None)
        if isinstance(briefing, dict):
            briefing = PolicyBriefing.model_validate(briefing)
        if isinstance(briefing, PolicyBriefing):
            log.info("briefing cites %s", ", ".join(briefing.cited_clauses) or "nothing")
            return briefing
        return None
    except Exception as error:  # the ruling stands with or without the briefing
        log.warning("LlamaIndex briefing unavailable: %s", error)
        return None


def _prompt(request: ScreeningRequest, verdict: ComplianceVerdict) -> str:
    traveller = request.traveller
    lines = [
        f"Trip {request.trip_ref} for {traveller.full_name}, grade "
        f"{traveller.grade}, {traveller.passport_country} passport.",
        f"{request.request.origin_iata} to {request.request.destination_iata}, "
        f"{request.request.depart_date} to {request.request.return_date}.",
        "",
        f"Binding ruling: {'within policy' if verdict.compliant else 'NOT within policy'}.",
        f"Manager approval required: {verdict.requires_manager_approval}.",
        "",
        "Findings:",
    ]
    lines += [
        f"  [{finding.severity}] {finding.clause_id} {finding.title}: {finding.detail}"
        for finding in verdict.findings
    ] or ["  (none)"]
    if verdict.visa:
        lines += [
            "",
            f"Entry: {verdict.visa.requirement} for a "
            f"{verdict.visa.passport_country} passport entering "
            f"{verdict.visa.destination_country}. {verdict.visa.notes}",
        ]
    return "\n".join(lines)
