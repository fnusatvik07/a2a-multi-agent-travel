"""TinyDB access for the document-shaped data.

Postgres is a poor fit for the things that read like documents rather than
rows: policy clauses with prose, per-country entry rules, customer site
records, and the append-only trace of everything the agents said to each
other. Those live in TinyDB, a zero-setup NoSQL store backed by JSON files you
can open in an editor while the demo runs.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from tinydb import Query, TinyDB

from .config import settings

POLICIES = "policies"
VISA_RULES = "visa_rules"
VENUES = "venues"

SEEDED_COLLECTIONS = (POLICIES, VISA_RULES, VENUES)


@cache
def _db(collection: str) -> TinyDB:
    directory = settings().tinydb_dir
    directory.mkdir(parents=True, exist_ok=True)
    return TinyDB(directory / f"{collection}.json", indent=2, sort_keys=False)


def table(collection: str) -> Any:
    """Return the default table of a TinyDB collection."""
    return _db(collection).table("_default")


def all_documents(collection: str) -> list[dict[str, Any]]:
    return [dict(doc) for doc in table(collection).all()]


def replace_all(collection: str, documents: list[dict[str, Any]]) -> None:
    """Replace a collection's contents. Used by the seeder."""
    handle = table(collection)
    handle.truncate()
    handle.insert_multiple(documents)


def find(collection: str, **equals: Any) -> list[dict[str, Any]]:
    """Return documents whose fields all equal the given values."""
    query = Query()
    condition = None
    for field, value in equals.items():
        clause = query[field] == value
        condition = clause if condition is None else (condition & clause)
    if condition is None:
        return all_documents(collection)
    return [dict(doc) for doc in table(collection).search(condition)]


def append(collection: str, document: dict[str, Any]) -> None:
    table(collection).insert(document)


def collections(prefix: str = "") -> list[str]:
    """Names of the collections on disk, optionally filtered by prefix."""
    directory = settings().tinydb_dir
    if not directory.exists():
        return []
    return sorted(
        path.stem
        for path in directory.glob(f"{prefix}*.json")
    )


def reset_all() -> None:
    """Drop the seeded collections. Used by the seeder and the test fixtures."""
    for collection in SEEDED_COLLECTIONS:
        table(collection).truncate()
