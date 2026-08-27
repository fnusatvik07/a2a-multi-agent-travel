"""Shared vocabulary and plumbing for the AtlasTrip agent network.

This package is deliberately thin. It holds the data contract the agents agree
on, the two storage adapters, and the small amount of A2A scaffolding that
would otherwise be copied five times. It contains no agent logic: each agent
lives in its own process, its own virtual environment and its own framework.
"""

from .config import Settings, settings
from .registry import ALL_AGENTS, BY_KEY, SPECIALISTS, AgentEndpoint

__all__ = [
    "ALL_AGENTS",
    "BY_KEY",
    "SPECIALISTS",
    "AgentEndpoint",
    "Settings",
    "settings",
]
