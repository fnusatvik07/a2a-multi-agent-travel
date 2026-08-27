"""Ledger as an A2A server, including the one interrupted task on the network.

Most A2A tasks run start to finish. This one does not. When policy says a human
has to approve the spend, Ledger moves the task to ``input-required`` and
returns. The task is not finished and it has not failed; it is waiting.

The caller sees the interruption on its stream, goes and gets the approval, and
sends a second message *on the same task id*. The framework routes it back
here, ``execute`` runs again with the approval token present, and the task
finishes. That is the whole human-in-the-loop mechanism, and it is a property
of the protocol rather than something this agent had to invent.
"""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part

from atlastrip_core import audit
from atlastrip_core.a2a_support import accept_task, data_part, read_request
from atlastrip_core.console import get_logger
from atlastrip_core.models import SpendRequest

from . import agent, service

log = get_logger("ledger")


class LedgerExecutor(AgentExecutor):
    """Turns an A2A request into a budget decision, pausing for a human when
    policy demands one."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        resuming = context.current_task is not None
        if not resuming:
            # Only a brand new task gets an opening Task event. On a resume the
            # task already exists and the caller is still holding its id.
            await accept_task(context, event_queue)

        updater = TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        )

        _, payload = read_request(context)
        try:
            request = SpendRequest.model_validate(payload)
        except Exception as error:
            await updater.reject(
                updater.new_agent_message(
                    [Part(text=f"That is not a spend request I can act on: {error}")]
                )
            )
            return

        audit.record(
            agent="ledger",
            direction="inbound",
            event="resumed" if resuming else "received",
            trip_ref=request.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            summary=f"${request.total_usd:,.2f} against {request.cost_center_id}",
        )
        log.info(
            "%s $%.2f for %s",
            "resuming" if resuming else "assessing",
            request.total_usd,
            request.trip_ref,
        )

        await updater.start_work(
            updater.new_agent_message(
                [Part(text=f"Checking {request.cost_center_id} against ${request.total_usd:,.2f}.")]
            )
        )

        try:
            # The binding decision. This is what may or may not move money.
            verdict = await service.assess(request)
        except Exception as error:
            log.warning("assessment failed for %s: %s", request.trip_ref, error)
            await updater.failed(
                updater.new_agent_message([Part(text=f"Could not assess the spend: {error}")])
            )
            return

        opinion = await agent.explain(request, verdict)
        if opinion is not None:
            verdict.reason = opinion.reason
            if opinion.concern:
                verdict.reason += f" Concern: {opinion.concern}"

        # The result is published either way, so a paused caller still gets the
        # numbers it needs to put in front of a human.
        await updater.add_artifact(
            parts=[data_part(verdict), Part(text=verdict.reason)],
            name="budget_verdict",
            last_chunk=True,
        )

        if verdict.decision == "needs_approval":
            token = service.authorization_code(request)
            await updater.requires_input(
                updater.new_agent_message(
                    [
                        Part(
                            text=(
                                f"{verdict.reason} To proceed, resend this "
                                f"request on the same task with "
                                f"manager_approval_token={token}."
                            )
                        )
                    ]
                )
            )
            audit.record(
                agent="ledger",
                direction="inbound",
                event="escalated",
                trip_ref=request.trip_ref,
                context_id=context.context_id,
                task_id=context.task_id,
                state="TASK_STATE_INPUT_REQUIRED",
                summary=f"awaiting approval for ${request.total_usd:,.2f}",
            )
            return

        await updater.complete(
            updater.new_agent_message([Part(text=f"{verdict.decision}: {verdict.reason}")])
        )
        audit.record(
            agent="ledger",
            direction="inbound",
            event="completed",
            trip_ref=request.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            state="TASK_STATE_COMPLETED",
            summary=f"{verdict.decision} ${verdict.requested_usd:,.2f}",
            payload={
                "decision": verdict.decision,
                "authorization_code": verdict.authorization_code,
                "remaining_after_usd": verdict.remaining_after_usd,
            },
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancelling an unapproved request is the normal way to abandon a trip."""
        await TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        ).cancel()
