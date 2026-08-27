"""The A2A protocol itself, exercised against a live agent.

These tests go under the SDK where it matters, so the repository can show what
the protocol actually looks like on the wire rather than only how the Python
client wraps it.
"""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from atlastrip_core import a2a_client
from atlastrip_core.models import FlightBrief, FlightProposal
from atlastrip_core.registry import SKYLINE


def flight_brief(trip_ref: str) -> FlightBrief:
    return FlightBrief(
        trip_ref=trip_ref,
        origin_iata="SFO",
        dest_iata="HND",
        depart_date="2026-10-14",
        return_date="2026-10-17",
        traveller_grade="IC5",
        preferred_carriers=["NH", "JL", "UA"],
    )


async def test_a_task_walks_the_whole_lifecycle(context_id, trip_ref):
    """submitted, then working, then an artifact, then completed."""
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source the best round trip.",
        payload=flight_brief(trip_ref),
        context_id=context_id,
        caller="test",
    )
    assert reply.state == "TASK_STATE_COMPLETED"
    assert reply.task_id
    assert reply.progress, "the caller should see progress while the agent works"
    assert reply.data is not None


async def test_the_structured_artifact_matches_the_shared_contract(context_id, trip_ref):
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source the best round trip.",
        payload=flight_brief(trip_ref),
        context_id=context_id,
        caller="test",
    )
    proposal = FlightProposal.model_validate(reply.data)
    assert proposal.trip_ref == trip_ref
    assert proposal.outbound.origin_iata == "SFO"
    assert proposal.inbound.origin_iata == "HND"
    assert proposal.total_usd == pytest.approx(
        proposal.outbound.total_usd + proposal.inbound.total_usd, abs=0.01
    )


async def test_the_context_id_is_carried_back(context_id, trip_ref):
    """One context id per trip is what makes the audit trail readable."""
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source the best round trip.",
        payload=flight_brief(trip_ref),
        context_id=context_id,
        caller="test",
    )
    assert reply.context_id == context_id


async def test_a_malformed_brief_is_rejected_rather_than_failed(context_id):
    """Rejected says the caller was wrong. Failed says the agent broke."""
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source flights.",
        payload={"this": "is not a flight brief"},
        context_id=context_id,
        caller="test",
    )
    assert reply.state == "TASK_STATE_REJECTED"


async def test_a_route_with_no_inventory_fails_the_task(context_id, trip_ref):
    """Nothing to sell is a failure of the task, not a malformed request."""
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source flights.",
        payload=flight_brief(trip_ref).model_copy(
            update={"origin_iata": "SYD", "dest_iata": "FRA"}
        ),
        context_id=context_id,
        caller="test",
    )
    assert reply.state == "TASK_STATE_FAILED"


async def test_a_completed_task_can_be_fetched_back_by_id(context_id, trip_ref):
    """Task state lives in Postgres, so it outlives the request that made it."""
    reply = await a2a_client.ask(
        SKYLINE,
        instruction="Source the best round trip.",
        payload=flight_brief(trip_ref),
        context_id=context_id,
        caller="test",
    )
    body = await _rpc("GetTask", {"id": reply.task_id})
    assert "error" not in body, body.get("error")
    assert body["result"]["id"] == reply.task_id


async def test_the_raw_json_rpc_binding_answers_a_send(context_id, trip_ref):
    """No SDK on the client side at all: this is the wire format.

    A2A 1.0 names its JSON-RPC methods after the gRPC service, so the method
    here is ``SendMessage`` rather than the ``message/send`` that material
    written against the 0.3 spec will show.
    """
    body = await _rpc("SendMessage", {"message": _message(context_id, trip_ref)})
    assert "error" not in body, body.get("error")
    assert "task" in body["result"] or "message" in body["result"]


async def test_a_client_written_against_the_0_3_spec_is_still_served(context_id, trip_ref):
    """Compatibility is switched on, so older clients keep working.

    The 0.3 message shape differs as well as the method name: the role is the
    lowercase string rather than the proto enum.
    """
    body = await _rpc(
        "message/send",
        {
            "message": {
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "Source the best round trip."},
                    {
                        "kind": "data",
                        "data": flight_brief(trip_ref).model_dump(mode="json"),
                    },
                ],
            }
        },
        version=None,
    )
    assert "error" not in body, body.get("error")


async def test_omitting_the_version_header_selects_the_compatibility_handler():
    """Worth knowing before debugging a puzzling version error: with
    compatibility enabled, a request that does not say which version it speaks
    is treated as 0.3."""
    body = await _rpc("GetTask", {"id": "does-not-exist"}, version=None)
    assert body.get("error", {}).get("code") == -32009


async def test_an_unknown_method_is_a_json_rpc_error_not_a_crash():
    body = await _rpc("does/notExist", {})
    assert body.get("error", {}).get("code") == -32601


def _message(context_id: str, trip_ref: str) -> dict:
    return {
        "messageId": str(uuid.uuid4()),
        "contextId": context_id,
        "role": "ROLE_USER",
        "parts": [
            {"text": "Source the best round trip."},
            {"data": flight_brief(trip_ref).model_dump(mode="json")},
        ],
    }


async def _rpc(method: str, params: dict, version: str | None = "1.0") -> dict:
    """One JSON-RPC call, with no A2A client library involved.

    ``A2A-Version`` is what tells a compatibility-enabled server which spec the
    caller speaks. Leave it off and the server assumes 0.3.
    """
    headers = {"Accept": "application/json, text/event-stream"}
    if version:
        headers["A2A-Version"] = version

    async with httpx.AsyncClient(timeout=90.0) as http:
        response = await http.post(
            SKYLINE.jsonrpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers=headers,
        )
    return _json_rpc(response)


def _json_rpc(response: httpx.Response) -> dict:
    """Read one JSON-RPC message, whichever way the server framed it."""
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise AssertionError("event stream carried no data frame")
    return response.json()
