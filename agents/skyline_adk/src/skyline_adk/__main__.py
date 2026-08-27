"""Run Skyline as an A2A server."""

from __future__ import annotations

from a2a.server.request_handlers import DefaultRequestHandler

from atlastrip_core.a2a_support import build_app, run
from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.db import build_task_store
from atlastrip_core.registry import SKYLINE

from .card import agent_card
from .executor import SkylineExecutor


def build_application():
    """Wire the executor to the A2A request handler and mount the routes."""
    card = agent_card()
    handler = DefaultRequestHandler(
        agent_executor=SkylineExecutor(),
        # Tasks are persisted in Postgres, so `tasks/get` still answers for a
        # task this process accepted before it was last restarted.
        task_store=build_task_store(),
        agent_card=card,
    )
    return build_app(agent_card=card, request_handler=handler)


def main() -> None:
    log = get_logger("skyline")
    log.info(
        "Skyline (Google ADK) on %s  [reasoning=%s]",
        SKYLINE.base_url,
        "llm" if settings().uses_llm else "deterministic",
    )
    run(build_application(), SKYLINE)


if __name__ == "__main__":
    main()
