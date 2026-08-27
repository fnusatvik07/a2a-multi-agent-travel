"""The Concierge as an A2A server.

Two things make this executor different from the four specialists.

The first is that it is a client as well as a server. While it is holding one
A2A task open for its caller, it is opening four more against its peers, all
sharing a context id.

The second is that it forwards an interruption. When Ledger pauses in
``input-required``, the LangGraph run suspends on an ``interrupt`` and this
executor puts *its own* task into ``input-required`` too. The pause therefore
propagates from the agent that needs the answer, through the orchestrator, out
to the person who can give it, without any of them special-casing the others.
"""

from __future__ import annotations

import uuid
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part
from langgraph.types import Command

from atlastrip_core import audit
from atlastrip_core.a2a_support import (
    accept_task,
    data_part,
    describe,
    read_request,
)
from atlastrip_core.console import get_logger

from . import graph as trip_graph
from .narrative import plain

log = get_logger("concierge")

DECLINE_WORDS = {"no", "decline", "reject", "deny", "cancel"}


class ConciergeExecutor(AgentExecutor):
    """Runs one trip through the LangGraph state machine."""

    def __init__(self) -> None:
        # Compiled once. The checkpointer inside it is what lets a suspended
        # trip be resumed on a later request.
        self._graph = trip_graph.compile_graph()

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        resuming = context.current_task is not None
        if not resuming:
            await accept_task(context, event_queue)

        updater = TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        )
        instruction, payload = read_request(context)

        # The LangGraph thread is keyed on the A2A task, so resuming the task
        # and resuming the graph are the same act.
        config: dict[str, Any] = {"configurable": {"thread_id": context.task_id}}

        if resuming:
            decision = _read_decision(instruction, payload)
            log.info(
                "resuming %s: %s",
                context.task_id,
                "approved" if decision["approved"] else "declined",
            )
            await updater.start_work(
                updater.new_agent_message(
                    [
                        Part(
                            text=(
                                "Approval received; settling with Ledger."
                                if decision["approved"]
                                else "Approval declined; standing the trip down."
                            )
                        )
                    ]
                )
            )
            command: Any = Command(resume=decision)
        else:
            trip_ref = _trip_ref(payload)
            await updater.start_work(
                updater.new_agent_message([Part(text=f"Planning {trip_ref}.")])
            )
            audit.record(
                agent="concierge",
                direction="inbound",
                event="received",
                trip_ref=trip_ref,
                context_id=context.context_id,
                task_id=context.task_id,
                summary=instruction[:160],
            )
            command = {
                "utterance": instruction,
                "trip_ref": trip_ref,
                "context_id": context.context_id or "",
                "journal": [],
            }

        try:
            state = await self._run(command, config, updater)
        except Exception as error:
            log.warning("planning failed: %s", describe(error))
            await updater.failed(
                updater.new_agent_message([Part(text=f"Planning failed: {describe(error)}")])
            )
            return

        if state is None:
            # The graph suspended. The task stays open, waiting on a human.
            return

        if state.get("error"):
            await updater.failed(
                updater.new_agent_message([Part(text=state["error"])])
            )
            audit.record(
                agent="concierge",
                direction="inbound",
                event="failed",
                trip_ref=state.get("trip_ref"),
                context_id=context.context_id,
                task_id=context.task_id,
                state="TASK_STATE_FAILED",
                summary=state["error"],
            )
            return

        itinerary = trip_graph.build_itinerary(state)
        itinerary.narrative = state.get("narrative") or plain(itinerary)

        await updater.add_artifact(
            parts=[data_part(itinerary), Part(text=itinerary.narrative)],
            name="itinerary",
            last_chunk=True,
        )
        await updater.complete(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            f"{itinerary.trip_ref} {itinerary.status.replace('_', ' ')}, "
                            f"${itinerary.total_usd:,.2f}."
                        )
                    )
                ]
            )
        )
        audit.record(
            agent="concierge",
            direction="inbound",
            event="completed",
            trip_ref=itinerary.trip_ref,
            context_id=context.context_id,
            task_id=context.task_id,
            state="TASK_STATE_COMPLETED",
            summary=f"{itinerary.status} ${itinerary.total_usd:,.2f}",
            payload={"status": itinerary.status, "total_usd": itinerary.total_usd},
        )

    async def _run(
        self, command: Any, config: dict[str, Any], updater: TaskUpdater
    ) -> dict[str, Any] | None:
        """Drive the graph, streaming its journal out as task progress.

        Returns the final state, or ``None`` when the graph suspended and the
        task has been left in ``input-required``.
        """
        # On a resume the checkpoint already holds everything the caller was
        # told before the pause, so start reporting from where we left off
        # rather than replaying the whole trip.
        existing = await self._graph.aget_state(config)
        reported = len(existing.values.get("journal", [])) if existing.values else 0

        async for chunk in self._graph.astream(
            command, config=config, stream_mode="values"
        ):
            journal = chunk.get("journal", [])
            for line in journal[reported:]:
                await updater.start_work(
                    updater.new_agent_message([Part(text=line)])
                )
            reported = len(journal)

        state = await self._graph.aget_state(config)
        if state.interrupts:
            await self._pause(state.interrupts[0].value, updater)
            return None
        return dict(state.values)

    async def _pause(self, request: Any, updater: TaskUpdater) -> None:
        """Put this task into input-required and stop, leaving it resumable."""
        question = (
            request.get("question", "Approval required.")
            if isinstance(request, dict)
            else str(request)
        )
        approver = (
            request.get("approver", "the cost centre owner")
            if isinstance(request, dict)
            else "the cost centre owner"
        )
        await updater.requires_input(
            updater.new_agent_message(
                [
                    Part(
                        text=(
                            f"{question} This needs {approver}. Reply on this "
                            f"task with approve or decline."
                        )
                    ),
                    data_part(request if isinstance(request, dict) else {}),
                ]
            )
        )
        audit.record(
            agent="concierge",
            direction="inbound",
            event="escalated",
            trip_ref=request.get("trip_ref") if isinstance(request, dict) else None,
            context_id=updater.context_id,
            task_id=updater.task_id,
            state="TASK_STATE_INPUT_REQUIRED",
            summary=question[:160],
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Abandoning a trip that is waiting on approval is a normal outcome."""
        await TaskUpdater(
            event_queue, context.task_id or "", context.context_id or ""
        ).cancel()


def _read_decision(instruction: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Work out whether the human said yes, from either half of the message."""
    if "approved" in payload:
        return {"approved": bool(payload["approved"])}
    words = set(instruction.lower().replace(".", " ").split())
    return {"approved": not (words & DECLINE_WORDS)}


def _trip_ref(payload: dict[str, Any]) -> str:
    given = payload.get("trip_ref")
    if isinstance(given, str) and given:
        return given
    return f"TRIP-{uuid.uuid4().hex[:8].upper()}"
