"""Postgres access for the operational travel data.

Postgres holds everything relational and transactional: airline inventory,
hotel rates, employees, cost centres and the budget ledger. It also backs the
A2A task store, so a restarted agent can still answer ``tasks/get`` for a task
it accepted before the restart.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from .config import settings


_pool: asyncpg.Pool | None = None


async def pool() -> asyncpg.Pool:
    """Return the process-wide connection pool, creating it on first use."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings().postgres_dsn, min_size=1, max_size=8
        )
    return _pool


async def close_pool() -> None:
    """Release the pool. Called from each service's shutdown hook."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def connection() -> AsyncIterator[asyncpg.Connection]:
    """Borrow a connection from the pool."""
    connection_pool = await pool()
    async with connection_pool.acquire() as conn:
        yield conn


async def fetch(query: str, *args: Any) -> list[dict[str, Any]]:
    """Run a query and return plain dictionaries."""
    async with connection() as conn:
        rows = await conn.fetch(query, *args)
    return [dict(row) for row in rows]


async def fetch_one(query: str, *args: Any) -> dict[str, Any] | None:
    """Run a query and return the first row, or ``None``."""
    async with connection() as conn:
        row = await conn.fetchrow(query, *args)
    return dict(row) if row else None


async def execute(query: str, *args: Any) -> str:
    """Run a statement and return the Postgres status tag."""
    async with connection() as conn:
        return await conn.execute(query, *args)


def build_task_store() -> Any:
    """Build the A2A task store backed by the same Postgres database.

    The SDK persists every ``Task`` it accepts here, which is what makes
    ``tasks/get`` and ``tasks/list`` survive a process restart. Import is local
    so that services which only need business queries do not pay for
    SQLAlchemy.
    """
    from a2a.server.tasks import DatabaseTaskStore
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(settings().sqlalchemy_dsn())
    return DatabaseTaskStore(engine=engine, table_name="a2a_tasks")
