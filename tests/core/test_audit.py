"""The audit trail is how the demo proves what happened, so it is tested."""

from __future__ import annotations

from atlastrip_core import audit


def test_the_trail_merges_every_service_in_time_order(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    audit.record(agent="concierge", direction="outbound", event="asked", context_id="c1")
    audit.record(agent="skyline", direction="inbound", event="received", context_id="c1")
    audit.record(agent="skyline", direction="inbound", event="completed", context_id="c1")
    audit.record(agent="hearth", direction="inbound", event="received", context_id="c2")

    trail = audit.trail("c1")
    assert [entry["agent"] for entry in trail] == ["concierge", "skyline", "skyline"]
    assert [entry["event"] for entry in trail] == ["asked", "received", "completed"]


def test_the_trail_is_narrowed_by_context(tmp_path, monkeypatch):
    """One context id per trip is what makes five processes readable as one story."""
    _isolate(tmp_path, monkeypatch)

    audit.record(agent="ledger", direction="inbound", event="received", context_id="c1")
    audit.record(agent="ledger", direction="inbound", event="received", context_id="c2")

    assert len(audit.trail("c1")) == 1
    assert len(audit.trail()) == 2


def _isolate(tmp_path, monkeypatch):
    """Point TinyDB at a scratch directory so tests never touch real data."""
    from atlastrip_core import config, documents

    config.settings.cache_clear()
    documents._db.cache_clear()
    monkeypatch.setenv("ATLASTRIP_TINYDB_DIR", str(tmp_path))
    config.settings.cache_clear()
