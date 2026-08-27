"""An append-only trace of every A2A exchange on the network.

Each agent writes one record when it accepts work and one when it finishes,
and the Concierge writes a pair around every call it makes. Reading the trail
back afterwards shows exactly what crossed the wire, which is far more
convincing than reading five sets of logs side by side.

Each service writes to its own TinyDB file. TinyDB keeps its document index in
memory and hands out sequential ids, so two processes writing to one file will
collide; one file per writer removes the contention entirely, and ``trail()``
merges them back into a single ordered view on read.
"""

from __future__ import annotations

import itertools
import threading
from datetime import UTC, datetime
from typing import Any

from . import documents

_sequence = itertools.count()
_lock = threading.Lock()

PREFIX = "audit_"


def collection_for(agent: str) -> str:
    return f"{PREFIX}{agent}"


def record(
    *,
    agent: str,
    direction: str,
    event: str,
    trip_ref: str | None = None,
    context_id: str | None = None,
    task_id: str | None = None,
    state: str | None = None,
    summary: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one line to this service's trail.

    Args:
        agent: The service writing the record, which selects the file.
        direction: ``inbound`` for work this agent accepted, ``outbound`` for
            a call it made to a peer.
        event: A short verb: ``received``, ``completed``, ``escalated``.
        summary: One line a human can read without unpacking the payload.
    """
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "seq": next(_sequence),
        "agent": agent,
        "direction": direction,
        "event": event,
        "trip_ref": trip_ref,
        "context_id": context_id or None,
        "task_id": task_id or None,
        "state": state,
        "summary": summary,
        "payload": payload or {},
    }
    with _lock:
        documents.append(collection_for(agent), entry)


def trail(context_id: str | None = None) -> list[dict[str, Any]]:
    """Merge every service's trail into one timeline.

    Narrow it with ``context_id`` to see a single trip, which is the whole
    point of threading one context id through all five agents.
    """
    entries: list[dict[str, Any]] = []
    for collection in documents.collections(prefix=PREFIX):
        entries.extend(documents.all_documents(collection))
    if context_id:
        entries = [entry for entry in entries if entry.get("context_id") == context_id]
    return sorted(entries, key=lambda entry: (entry["at"], entry.get("seq", 0)))


def clear() -> None:
    """Wipe every service's trail. Used between demo runs and in tests."""
    for collection in documents.collections(prefix=PREFIX):
        documents.table(collection).truncate()
