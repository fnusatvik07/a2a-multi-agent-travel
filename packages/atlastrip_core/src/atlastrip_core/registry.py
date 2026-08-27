"""The network directory: who is on the network, and where to reach them.

In a production deployment this would be a service registry or a catalogue of
Agent Card URLs. Here it is a small, explicit table so that a reader can see
the entire topology of the network on one screen.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import settings


@dataclass(frozen=True)
class AgentEndpoint:
    """One agent service on the AtlasTrip network."""

    key: str
    """Short identifier used in code, logs and the audit trail."""

    name: str
    """Human-facing name published on the Agent Card."""

    framework: str
    """The agent framework this service is implemented with."""

    role: str
    """One line describing what this agent is responsible for."""

    skill_id: str
    """The A2A skill the agent advertises and that peers invoke."""

    port: int

    @property
    def base_url(self) -> str:
        return f"http://{settings().host}:{self.port}"

    @property
    def agent_card_url(self) -> str:
        return f"{self.base_url}/.well-known/agent-card.json"

    @property
    def jsonrpc_url(self) -> str:
        return f"{self.base_url}{JSONRPC_PATH}"

    @property
    def rest_url(self) -> str:
        return f"{self.base_url}{REST_PREFIX}"


# Path layout shared by every agent, so one URL shape works across the network.
JSONRPC_PATH = "/a2a/jsonrpc"
REST_PREFIX = "/a2a/rest"


CONCIERGE = AgentEndpoint(
    key="concierge",
    name="Concierge",
    framework="LangGraph",
    role="Orchestrates a trip end to end and talks to the traveller.",
    skill_id="plan_trip",
    port=8000,
)

SKYLINE = AgentEndpoint(
    key="skyline",
    name="Skyline",
    framework="Google ADK",
    role="Sources and ranks flight options against the traveller's constraints.",
    skill_id="source_flights",
    port=8001,
)

HEARTH = AgentEndpoint(
    key="hearth",
    name="Hearth",
    framework="CrewAI",
    role="Shortlists lodging near the meeting venue and applies corporate rates.",
    skill_id="source_stay",
    port=8002,
)

SENTINEL = AgentEndpoint(
    key="sentinel",
    name="Sentinel",
    framework="LlamaIndex",
    role="Screens the trip against travel policy and entry/visa rules.",
    skill_id="screen_trip",
    port=8003,
)

LEDGER = AgentEndpoint(
    key="ledger",
    name="Ledger",
    framework="Pydantic AI",
    role="Checks the cost centre budget and authorises or escalates the spend.",
    skill_id="authorize_spend",
    port=8004,
)

SPECIALISTS: tuple[AgentEndpoint, ...] = (SKYLINE, HEARTH, SENTINEL, LEDGER)
ALL_AGENTS: tuple[AgentEndpoint, ...] = (CONCIERGE, *SPECIALISTS)

BY_KEY: dict[str, AgentEndpoint] = {agent.key: agent for agent in ALL_AGENTS}

MCP_PORT = 8100
"""Port of the shared travel inventory MCP server."""
