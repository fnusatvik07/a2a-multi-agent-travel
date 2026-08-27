"""Run Ledger as an A2A server."""

from __future__ import annotations

from a2a.server.request_handlers import DefaultRequestHandler

from atlastrip_core.a2a_support import build_app, run
from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.db import build_task_store
from atlastrip_core.registry import LEDGER

from .card import agent_card
from .executor import LedgerExecutor


def build_application():
    card = agent_card()
    handler = DefaultRequestHandler(
        agent_executor=LedgerExecutor(),
        # Persistence matters more here than anywhere else: a task that is
        # waiting on a human may outlive the process it started in.
        task_store=build_task_store(),
        agent_card=card,
    )
    return build_app(agent_card=card, request_handler=handler)


def main() -> None:
    log = get_logger("ledger")
    log.info(
        "Ledger (Pydantic AI) on %s  [reasoning=%s]",
        LEDGER.base_url,
        "llm" if settings().uses_llm else "deterministic",
    )
    run(build_application(), LEDGER)


if __name__ == "__main__":
    main()
