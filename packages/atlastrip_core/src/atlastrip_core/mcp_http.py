"""A minimal Model Context Protocol client, written against the wire format.

Each agent framework ships its own MCP client, and they pin different, mutually
incompatible versions of the ``mcp`` package. This module exists so the shared
code can reach the inventory server without joining that argument, and because
seeing MCP as it actually travels is more instructive than seeing it wrapped.

The streamable HTTP transport is not complicated:

1. ``POST`` a JSON-RPC ``initialize`` request. The response carries an
   ``Mcp-Session-Id`` header that identifies the session from then on.
2. ``POST`` a ``notifications/initialized`` notification to finish the
   handshake.
3. ``POST`` ``tools/call`` requests for as long as you like.

Responses come back either as plain JSON or as a one-event SSE stream,
depending on what the server feels like doing, so both are handled.
"""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any

import httpx

from .config import settings

PROTOCOL_VERSION = "2025-06-18"

_ACCEPT = "application/json, text/event-stream"


class MCPError(RuntimeError):
    """The server returned a JSON-RPC error or an unusable tool result."""


class MCPClient:
    """One session against one MCP server."""

    def __init__(self, url: str | None = None, *, timeout: float = 30.0) -> None:
        self.url = url or settings().mcp_url
        self._http = httpx.AsyncClient(timeout=timeout)
        self._session_id: str | None = None
        self._next_id = 0

    async def __aenter__(self) -> MCPClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def connect(self) -> dict[str, Any]:
        """Perform the MCP handshake and return the server's capabilities."""
        response = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "atlastrip-core", "version": "1.0.0"},
                },
            }
        )
        self._session_id = response.headers.get("mcp-session-id")
        result = _result(_decode(response))
        await self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            expect_response=False,
        )
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the tool descriptors the server advertises."""
        payload = await self._request("tools/list", {})
        return payload.get("tools", [])

    async def call(self, tool: str, **arguments: Any) -> list[dict[str, Any]]:
        """Call a tool and return its results as a list of dictionaries.

        Every AtlasTrip tool answers with JSON, either one object or a list of
        them, so the return type is uniform and callers never branch on shape.
        """
        payload = await self._request(
            "tools/call", {"name": tool, "arguments": _prune(arguments)}
        )
        if payload.get("isError"):
            raise MCPError(f"{tool}: {_text_of(payload)}")

        records: list[dict[str, Any]] = []
        for block in payload.get("content", []):
            if block.get("type") != "text":
                continue
            decoded = json.loads(block["text"])
            records.extend(decoded if isinstance(decoded, list) else [decoded])
        return records

    async def call_one(self, tool: str, **arguments: Any) -> dict[str, Any] | None:
        """Call a tool that answers with a single record."""
        records = await self.call(tool, **arguments)
        return records[0] if records else None

    async def aclose(self) -> None:
        await self._http.aclose()

    # -- internals ---------------------------------------------------------

    def _request_id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        response = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._request_id(),
                "method": method,
                "params": params,
            }
        )
        return _result(_decode(response))

    async def _post(
        self, body: dict[str, Any], *, expect_response: bool = True
    ) -> httpx.Response:
        headers = {"Content-Type": "application/json", "Accept": _ACCEPT}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        response = await self._http.post(self.url, json=body, headers=headers)
        if expect_response and response.status_code >= 400:
            raise MCPError(f"{response.status_code} from MCP server: {response.text}")
        return response


def _decode(response: httpx.Response) -> dict[str, Any]:
    """Read a JSON-RPC message out of a JSON body or a one-event SSE stream."""
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise MCPError("event stream carried no data frame")
    return response.json()


def _result(message: dict[str, Any]) -> dict[str, Any]:
    if "error" in message:
        error = message["error"]
        raise MCPError(f"{error.get('code')}: {error.get('message')}")
    return message.get("result", {})


def _text_of(payload: dict[str, Any]) -> str:
    return " ".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    )


def _prune(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None`` arguments so servers see absent rather than null."""
    return {key: value for key, value in arguments.items() if value is not None}
