"""Sentinel as an A2A server."""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part

from atlastrip_core import audit
from atlastrip_core.a2a_support import accept_task, data_part, read_request
from atlastrip_core.console import get_logger
from atlastrip_core.models import ScreeningRequest

from . import agent, service

log = get_logger("sentinel")


class SentinelExecutor(AgentExecutor):
    """Turns an A2A request into a compliance verdict."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        await accept_task(context, event_queue)
        updater = TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        )

        _, payload = read_request(context)
        try:
            request = ScreeningRequest.model_validate(payload)
        except Exception as error:
            await updater.reject(
                updater.new_agent_message(
                    [Part(text=f"That is not a screening request I can act on: {error}")]
                )
            )
            return

        audit.record(
            agent="sentinel",
            direction="inbound",
            event="received",
            trip_ref=request.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            summary=f"screening {request.request.origin_iata}->{request.request.destination_iata}",
        )
        log.info("screening %s", request.trip_ref)

        await updater.start_work(
            updater.new_agent_message([Part(text="Evaluating the policy book.")])
        )

        try:
            # The binding ruling. Deterministic, and independent of any model.
            verdict = await service.screen(request)
        except Exception as error:
            log.warning("screening failed for %s: %s", request.trip_ref, error)
            await updater.failed(
                updater.new_agent_message([Part(text=f"Could not screen the trip: {error}")])
            )
            return

        await updater.start_work(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            f"{len(verdict.findings)} findings. "
                            f"Retrieving the clauses that explain them."
                        )
                    )
                ]
            )
        )

        # The explanation. Retrieval-grounded, and allowed to fail.
        briefing = await agent.explain(request, verdict)
        if briefing is not None:
            verdict.summary = briefing.summary
            if briefing.next_step:
                verdict.summary += f" Next: {briefing.next_step}"

        await updater.add_artifact(
            parts=[data_part(verdict), Part(text=verdict.summary)],
            name="compliance_verdict",
            last_chunk=True,
        )
        standing = "Within policy" if verdict.compliant else "Not within policy"
        approval = "required" if verdict.requires_manager_approval else "not required"
        await updater.complete(
            updater.new_agent_message(
                [Part(text=f"{standing}; manager approval {approval}.")]
            )
        )
        audit.record(
            agent="sentinel",
            direction="inbound",
            event="completed",
            trip_ref=request.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            state="TASK_STATE_COMPLETED",
            summary=verdict.summary,
            payload={
                "compliant": verdict.compliant,
                "requires_manager_approval": verdict.requires_manager_approval,
                "violations": [
                    f.clause_id for f in verdict.findings if f.severity == "violation"
                ],
            },
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        ).cancel()
