"""Skyline as an A2A server.

This file is where the protocol lives, and it is deliberately written out in
full rather than hidden behind a base class: reading it end to end shows you
the entire server side of A2A.

The shape of a task is always the same:

    Task(submitted)  ->  working  ->  artifact  ->  completed
                                  \\-> failed

The caller sees each of those as an event on its stream.
"""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part

from atlastrip_core import audit
from atlastrip_core.a2a_support import (
    accept_task,
    data_part,
    describe,
    read_request,
)
from atlastrip_core.console import get_logger
from atlastrip_core.models import FlightBrief

from . import agent, service

log = get_logger("skyline")


class SkylineExecutor(AgentExecutor):
    """Turns an A2A request into a flight proposal."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        # 1. Acknowledge. The caller now has a task id it can poll or cancel.
        await accept_task(context, event_queue)
        updater = TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        )

        _, payload = read_request(context)
        try:
            brief = FlightBrief.model_validate(payload)
        except Exception as error:
            # A malformed brief is the caller's mistake, not a server fault,
            # so the task is rejected rather than failed.
            await updater.reject(
                updater.new_agent_message(
                    [Part(text=f"That is not a flight brief I can act on: {describe(error)}")]
                )
            )
            return

        audit.record(
            agent="skyline",
            direction="inbound",
            event="received",
            trip_ref=brief.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            summary=f"{brief.origin_iata}->{brief.dest_iata} {brief.depart_date}",
        )
        log.info(
            "sourcing %s->%s for %s", brief.origin_iata, brief.dest_iata, brief.trip_ref
        )

        # 2. Move to working, and keep the caller informed as we go. Every one
        #    of these is a TaskStatusUpdateEvent on the caller's stream.
        await updater.start_work(
            updater.new_agent_message([Part(text="Searching fare inventory.")])
        )

        try:
            candidates = await service.shortlist(brief)
            if not candidates["outbound"] or not candidates["inbound"]:
                raise LookupError(
                    f"No inventory for {brief.origin_iata}-{brief.dest_iata} "
                    f"on those dates."
                )

            # A second working update. The task stays in `working`; the caller
            # just gets another line of progress on its stream.
            await updater.start_work(
                updater.new_agent_message(
                    [
                        Part(
                            text=(
                                f"{len(candidates['outbound'])} outbound and "
                                f"{len(candidates['inbound'])} return fares "
                                f"shortlisted. Choosing."
                            )
                        )
                    ]
                )
            )

            selection = await agent.choose(brief, candidates)
            proposal = service.assemble(
                brief,
                candidates,
                outbound_offer_id=selection.outbound_offer_id,
                inbound_offer_id=selection.inbound_offer_id,
                rationale=selection.rationale,
            )
        except Exception as error:
            log.warning(
                "flight sourcing failed for %s: %s", brief.trip_ref, describe(error)
            )
            await updater.failed(
                updater.new_agent_message(
                    [Part(text=f"Could not source flights: {describe(error)}")]
                )
            )
            audit.record(
                agent="skyline",
                direction="inbound",
                event="failed",
                trip_ref=brief.trip_ref,
                context_id=context.context_id,
                task_id=context.task_id,
                state="TASK_STATE_FAILED",
                summary=str(error),
            )
            return

        # 3. Publish the result. The structured part is what the Concierge
        #    consumes; the text part is what a human reads in the CLI.
        await updater.add_artifact(
            parts=[data_part(proposal), Part(text=proposal.rationale)],
            name="flight_proposal",
            last_chunk=True,
        )

        # 4. Close the task. After a terminal state nothing more may be sent.
        await updater.complete(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            f"{proposal.outbound.carrier} "
                            f"{proposal.outbound.flight_no} out, "
                            f"{proposal.inbound.flight_no} back, "
                            f"${proposal.total_usd:,.2f} total."
                        )
                    )
                ]
            )
        )
        audit.record(
            agent="skyline",
            direction="inbound",
            event="completed",
            trip_ref=brief.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            state="TASK_STATE_COMPLETED",
            summary=f"${proposal.total_usd:,.2f} round trip",
            payload={"total_usd": proposal.total_usd, "cabin": proposal.outbound.cabin},
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Flight sourcing is short, so cancellation just closes the task."""
        await TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        ).cancel()
