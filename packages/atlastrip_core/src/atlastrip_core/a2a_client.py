"""Client-side glue: how one AtlasTrip agent calls another.

The Concierge uses this to reach the four specialists, and the demo CLI uses
the very same code path to reach the Concierge. That symmetry is the point of
A2A: an orchestrator is just another client, and an agent that orchestrates is
still an ordinary agent to whoever calls it.
"""

from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from typing import Any

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, get_message_text, get_text_parts
from a2a.types import AgentCard, Message, Part, Role, SendMessageRequest, TaskState

from . import audit
from .a2a_support import data_part
from .config import settings
from .registry import AgentEndpoint


@dataclass
class AgentReply:
    """Everything one agent-to-agent call produced, flattened for the caller."""

    agent: str
    task_id: str
    context_id: str
    state: str
    """The terminal ``TaskState`` name, e.g. ``TASK_STATE_COMPLETED``."""

    data: dict[str, Any] | None = None
    """The first structured artifact the agent returned, if any."""

    artifacts: list[dict[str, Any]] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    progress: list[str] = field(default_factory=list)
    """Human-readable status messages seen while the task was running."""

    @property
    def completed(self) -> bool:
        return self.state == "TASK_STATE_COMPLETED"

    @property
    def needs_input(self) -> bool:
        return self.state == "TASK_STATE_INPUT_REQUIRED"

    @property
    def question(self) -> str:
        """The last thing the agent said, which for an interrupted task is
        the question it is waiting on."""
        return self.progress[-1] if self.progress else ""


async def fetch_agent_card(endpoint: AgentEndpoint) -> AgentCard:
    """Read a peer's Agent Card. This is A2A discovery in one line."""
    from a2a.client import A2ACardResolver

    async with httpx.AsyncClient(timeout=15.0) as http:
        return await A2ACardResolver(http, endpoint.base_url).get_agent_card()


async def ask(
    endpoint: AgentEndpoint,
    *,
    instruction: str,
    payload: Any = None,
    context_id: str,
    task_id: str | None = None,
    caller: str = "client",
    trip_ref: str | None = None,
) -> AgentReply:
    """Send one message to an agent and consume its event stream to the end.

    Args:
        instruction: Natural language for the receiving agent's model.
        payload: A pydantic model or dict sent alongside as a structured part.
        context_id: Ties every call for one trip into a single conversation.
            All five agents see the same context id, which is what makes the
            trace in the audit trail readable.
        task_id: Set to continue an existing task, for example to answer an
            agent that stopped in ``input-required``.
    """
    parts: list[Part] = [Part(text=instruction)]
    if payload is not None:
        parts.append(data_part(payload))

    message = Message(
        role=Role.ROLE_USER,
        message_id=str(uuid.uuid4()),
        parts=parts,
        context_id=context_id,
        task_id=task_id or "",
    )

    audit.record(
        agent=caller,
        direction="outbound",
        event="asked",
        trip_ref=trip_ref,
        context_id=context_id,
        task_id=task_id,
        summary=f"{caller} -> {endpoint.key}: {instruction[:120]}",
    )

    # An agent that has to consult a model, and possibly a second agent behind
    # it, is not a sub-second call. The default HTTP timeout is far too short
    # for that, so the transport gets an explicit one.
    http = httpx.AsyncClient(timeout=settings().call_timeout_seconds)
    client = await create_client(
        endpoint.base_url,
        client_config=ClientConfig(streaming=True, httpx_client=http),
    )
    reply = AgentReply(
        agent=endpoint.key, task_id=task_id or "", context_id=context_id, state=""
    )
    try:
        async for event in client.send_message(SendMessageRequest(message=message)):
            _absorb(event, reply)
    finally:
        await client.close()
        await http.aclose()

    audit.record(
        agent=caller,
        direction="outbound",
        event="answered",
        trip_ref=trip_ref,
        context_id=context_id,
        task_id=reply.task_id,
        state=reply.state,
        summary=f"{endpoint.key} -> {caller}: {reply.state}",
        payload=reply.data or {},
    )
    return reply


def _absorb(event: Any, reply: AgentReply) -> None:
    """Fold one streamed A2A event into the accumulating reply.

    A streaming response is a sequence of one ``Task``, then any number of
    status and artifact updates, and finally a terminal status. An agent may
    also answer with a bare ``Message`` when it has nothing task-shaped to say.
    """
    if event.HasField("message"):
        reply.texts.append(get_message_text(event.message, delimiter=" "))
        reply.state = reply.state or "TASK_STATE_COMPLETED"
        return

    if event.HasField("task"):
        reply.task_id = event.task.id
        reply.context_id = event.task.context_id or reply.context_id
        reply.state = TaskState.Name(event.task.status.state)
        return

    if event.HasField("status_update"):
        status = event.status_update.status
        reply.state = TaskState.Name(status.state)
        if status.HasField("message"):
            text = get_message_text(status.message, delimiter=" ").strip()
            if text:
                reply.progress.append(text)
        return

    if event.HasField("artifact_update"):
        artifact = event.artifact_update.artifact
        for payload in get_data_parts(artifact.parts):
            reply.artifacts.append(payload)
            if reply.data is None:
                reply.data = payload
        text = "\n".join(get_text_parts(artifact.parts)).strip()
        if text:
            reply.texts.append(text)
