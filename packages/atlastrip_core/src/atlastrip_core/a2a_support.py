"""Server-side glue shared by all five agents.

The A2A lifecycle itself is written out in full inside each agent's
``executor.py`` so that opening any one agent shows you the whole protocol.
What lives here is only the repetitive scaffolding around it: describing the
agent on its Agent Card, reading a request out of an incoming message, and
putting a Starlette app on a port.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from a2a.helpers import get_data_parts, get_text_parts, new_data_part
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TaskStatus,
)
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import db
from .config import settings
from .registry import JSONRPC_PATH, REST_PREFIX, AgentEndpoint

PROTOCOL_VERSION = "1.0"
ORGANISATION = "Nimbus Robotics (AtlasTrip)"


def build_agent_card(
    endpoint: AgentEndpoint,
    *,
    description: str,
    skills: Sequence[AgentSkill],
    input_modes: Sequence[str] = ("text", "data"),
    output_modes: Sequence[str] = ("text", "data"),
) -> AgentCard:
    """Describe an agent so that peers can discover and call it.

    The card is served at ``/.well-known/agent-card.json``. It is the only
    thing a peer needs in order to talk to this agent: the interfaces list
    tells the client which transports are available and at which URLs, and the
    skills list tells it what the agent is willing to do.
    """
    return AgentCard(
        name=endpoint.name,
        description=description,
        version="1.0.0",
        provider=AgentProvider(
            organization=ORGANISATION, url="https://github.com/fnusatvik07/a2a-multi-agent-travel"
        ),
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=list(input_modes),
        default_output_modes=list(output_modes),
        skills=list(skills),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version=PROTOCOL_VERSION,
                url=f"{endpoint.base_url}{JSONRPC_PATH}",
            ),
            AgentInterface(
                protocol_binding="HTTP+JSON",
                protocol_version=PROTOCOL_VERSION,
                url=f"{endpoint.base_url}{REST_PREFIX}",
            ),
        ],
    )


def read_request(context: RequestContext) -> tuple[str, dict[str, Any]]:
    """Split an incoming A2A message into its human half and its machine half.

    Every AtlasTrip request carries two parts: a text part written for the
    receiving agent's language model, and a data part carrying the validated
    payload. An agent uses whichever it needs; both travel in the same message.
    """
    message = context.message
    if message is None:
        return "", {}
    instruction = "\n".join(get_text_parts(message.parts)).strip()
    data_parts = get_data_parts(message.parts)
    payload = data_parts[0] if data_parts else {}
    return instruction, payload


async def accept_task(context: RequestContext, event_queue: EventQueue) -> None:
    """Publish the initial ``Task``, which every A2A response must start with.

    The protocol requires a task-shaped response to open with the ``Task``
    object itself; status updates that arrive before it are rejected by the
    client. Doing this first also gives the caller a task id it can poll or
    cancel while the agent is still working.
    """
    await event_queue.enqueue_event(
        Task(
            id=context.task_id,
            context_id=context.context_id,
            status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
            history=[context.message] if context.message else [],
        )
    )


def describe(error: BaseException) -> str:
    """A message that is useful even when the exception has none.

    Several exception types, ``httpx.ReadTimeout`` among them, stringify to the
    empty string. An agent that reports a bare "could not do it" leaves the
    caller with nothing to act on, so the type name always appears.
    """
    detail = str(error).strip()
    return f"{type(error).__name__}: {detail}" if detail else type(error).__name__


def data_part(payload: Any) -> Part:
    """Wrap a pydantic model or dictionary as an A2A structured data part."""
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return new_data_part(payload)


def build_app(
    *,
    agent_card: AgentCard,
    request_handler: DefaultRequestHandler,
    extra_routes: Sequence[Route] = (),
) -> Starlette:
    """Mount the A2A endpoints of one agent onto a Starlette application.

    Three route groups make up an A2A server:

    * the Agent Card, served at the well-known path so peers can discover it;
    * the JSON-RPC binding, which also carries the streaming (SSE) methods;
    * the HTTP+JSON binding, for callers that prefer plain REST.
    """

    async def health(_: Any) -> JSONResponse:
        return JSONResponse({"status": "ok", "agent": agent_card.name})

    routes: list[Route] = [
        *create_agent_card_routes(agent_card=agent_card),
        Route("/healthz", health, methods=["GET"]),
        *extra_routes,
        # These go last: the JSON-RPC binding registers a tenant-scoped
        # catch-all that would otherwise shadow the routes above.
        #
        # `enable_v0_3_compat` makes each endpoint answer to the older spelling
        # of the methods as well. A2A 1.0 renamed the JSON-RPC methods to match
        # the gRPC service ("SendMessage" rather than "message/send"), and most
        # material written before the 1.0 spec uses the old names. Accepting
        # both costs nothing and means an older client still works.
        *create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url=JSONRPC_PATH,
            enable_v0_3_compat=True,
        ),
        *create_rest_routes(
            request_handler=request_handler,
            path_prefix=REST_PREFIX,
            enable_v0_3_compat=True,
        ),
    ]

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        yield
        await db.close_pool()

    return Starlette(routes=routes, lifespan=lifespan)


def run(app: Starlette, endpoint: AgentEndpoint) -> None:
    """Serve one agent on its registered port."""
    uvicorn.run(
        app,
        host=settings().host,
        port=endpoint.port,
        log_level="warning",
        access_log=False,
    )
