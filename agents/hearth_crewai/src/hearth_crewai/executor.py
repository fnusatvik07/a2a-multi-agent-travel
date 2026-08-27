"""Hearth as an A2A server.

Same protocol shape as every other agent on the network: acknowledge the task,
report progress while working, publish one structured artifact, close the task.
"""

from __future__ import annotations

from atlastrip_core import audit
from atlastrip_core.a2a_support import accept_task, data_part, read_request
from atlastrip_core.console import get_logger
from atlastrip_core.models import StayBrief
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part

from . import agent, service


log = get_logger("hearth")


class HearthExecutor(AgentExecutor):
    """Turns an A2A request into a lodging proposal."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        await accept_task(context, event_queue)
        updater = TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        )

        _, payload = read_request(context)
        try:
            brief = StayBrief.model_validate(payload)
        except Exception as error:
            await updater.reject(
                updater.new_agent_message(
                    [Part(text=f"That is not a stay brief I can act on: {error}")]
                )
            )
            return

        audit.record(
            agent="hearth",
            direction="inbound",
            event="received",
            trip_ref=brief.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            summary=(
                f"{brief.city} {brief.check_in}..{brief.check_out}"
                + (" (cap enforced)" if brief.enforce_cap else "")
            ),
        )
        log.info(
            "sourcing a stay in %s for %s%s",
            brief.city,
            brief.trip_ref,
            " with the cap enforced" if brief.enforce_cap else "",
        )

        await updater.start_work(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            "Looking for rooms near the venue"
                            + (
                                f" under ${brief.nightly_cap_usd:,.2f} a night."
                                if brief.enforce_cap and brief.nightly_cap_usd
                                else "."
                            )
                        )
                    )
                ]
            )
        )

        try:
            candidates = await service.shortlist(brief)
            if not candidates:
                raise LookupError(
                    f"Nothing in {brief.city} matches the brief"
                    + (
                        f" under ${brief.nightly_cap_usd:,.2f} a night."
                        if brief.enforce_cap and brief.nightly_cap_usd
                        else "."
                    )
                )

            await updater.start_work(
                updater.new_agent_message(
                    [Part(text=f"{len(candidates)} properties shortlisted. Deciding.")]
                )
            )

            selection = await agent.choose(brief, candidates)
            proposal = service.assemble(
                brief,
                candidates,
                offer_id=selection.offer_id if selection else None,
                rationale=selection.rationale if selection else "",
            )
        except Exception as error:
            log.warning("stay sourcing failed for %s: %s", brief.trip_ref, error)
            await updater.failed(
                updater.new_agent_message([Part(text=f"Could not source a stay: {error}")])
            )
            audit.record(
                agent="hearth",
                direction="inbound",
                event="failed",
                trip_ref=brief.trip_ref,
                context_id=context.context_id,
                task_id=context.task_id,
                state="TASK_STATE_FAILED",
                summary=str(error),
            )
            return

        await updater.add_artifact(
            parts=[data_part(proposal), Part(text=proposal.rationale)],
            name="stay_proposal",
            last_chunk=True,
        )
        await updater.complete(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            f"{proposal.recommended.name}, "
                            f"${proposal.recommended.nightly_rate_usd:,.2f} a night, "
                            f"${proposal.total_usd:,.2f} for the stay."
                        )
                    )
                ]
            )
        )
        audit.record(
            agent="hearth",
            direction="inbound",
            event="completed",
            trip_ref=brief.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            state="TASK_STATE_COMPLETED",
            summary=f"{proposal.recommended.name} ${proposal.total_usd:,.2f}",
            payload={
                "hotel": proposal.recommended.name,
                "nightly_rate_usd": proposal.recommended.nightly_rate_usd,
                "total_usd": proposal.total_usd,
            },
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        ).cancel()
