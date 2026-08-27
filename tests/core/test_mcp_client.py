"""The hand-written MCP client parses whatever the transport hands it."""

from __future__ import annotations

import json

import httpx
import pytest

from atlastrip_core.mcp_http import MCPClient, MCPError, _decode, _prune


def _response(body: str, content_type: str) -> httpx.Response:
    return httpx.Response(
        200, content=body.encode(), headers={"content-type": content_type}
    )


def test_a_plain_json_body_is_read_directly():
    message = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
    assert _decode(_response(json.dumps(message), "application/json")) == message


def test_a_server_sent_event_body_is_unwrapped():
    """Streamable HTTP may answer either way, sometimes for the same method."""
    message = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
    body = f"event: message\ndata: {json.dumps(message)}\n\n"
    assert _decode(_response(body, "text/event-stream")) == message


def test_an_event_stream_with_no_data_frame_is_an_error():
    with pytest.raises(MCPError):
        _decode(_response("event: ping\n\n", "text/event-stream"))


def test_absent_arguments_are_omitted_rather_than_sent_as_null():
    """A null cap and an absent cap mean different things to the server."""
    assert _prune({"city": "Tokyo", "max_nightly_rate": None}) == {"city": "Tokyo"}


def test_the_client_defaults_to_the_configured_server():
    from atlastrip_core.config import settings

    assert MCPClient().url == settings().mcp_url
