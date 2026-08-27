"""Fixtures for the integration tests.

These talk to the running network exactly as any other client would. Nothing
in this directory imports agent code.
"""

from __future__ import annotations

import json
import socket
import uuid

import pytest

import asyncpg

from atlastrip_core.config import REPO_ROOT, settings
from atlastrip_core.registry import ALL_AGENTS, MCP_PORT


def _listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.4)
        return probe.connect_ex((settings().host, port)) == 0


@pytest.fixture(autouse=True)
def skip_unless_the_network_is_running():
    """Skip rather than fail when the network is not up.

    Cloning the repository and running the tests should not produce a wall of
    connection errors; it should say plainly what to start.
    """
    down = [
        name
        for name, port in [
            ("inventory MCP", MCP_PORT),
            *[(agent.name, agent.port) for agent in ALL_AGENTS],
        ]
        if not _listening(port)
    ]
    if down:
        pytest.skip(f"not running: {', '.join(down)}. Start it with 'make run'.")


@pytest.fixture
def context_id() -> str:
    """A fresh conversation id, so tests never see each other's tasks."""
    return f"ctx-test-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def trip_ref() -> str:
    return f"TEST-{uuid.uuid4().hex[:8].upper()}"


# The tests below use their own short-lived connections rather than the shared
# pool in `atlastrip_core.db`. That pool is bound to the event loop that
# created it, and pytest-asyncio gives each test a fresh loop, so a pooled
# connection reused across tests fails in ways that are tedious to diagnose.


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(dsn=settings().postgres_dsn)


@pytest.fixture(scope="session", autouse=True)
async def restore_the_seeded_ledger():
    """Put the budget ledger back the way the seeder left it.

    Ledger commits real money. Running the demo, or these tests, spends some of
    the quarter's budget, and a later run would then fail for reasons that have
    nothing to do with the code. Restoring the seeded rows once per session
    makes every run start from the same position.
    """
    seeded = json.loads(
        (REPO_ROOT / "data" / "seed" / "budget_ledger.json").read_text()
    )
    connection = await _connect()
    try:
        await connection.execute("TRUNCATE budget_ledger RESTART IDENTITY")
        await connection.executemany(
            "INSERT INTO budget_ledger (cost_center_id, trip_ref, description,"
            " amount_usd, kind) VALUES ($1, $2, $3, $4, $5)",
            [
                (
                    row["cost_center_id"],
                    row["trip_ref"],
                    row["description"],
                    row["amount_usd"],
                    row["kind"],
                )
                for row in seeded
            ],
        )
    finally:
        await connection.close()
    yield


@pytest.fixture(autouse=True)
async def undo_commitments_made_by_this_test():
    """Remove whatever the test just authorised, so the next one starts level."""
    yield
    connection = await _connect()
    try:
        await connection.execute(
            "DELETE FROM budget_ledger WHERE trip_ref LIKE 'TEST-%'"
        )
    finally:
        await connection.close()
