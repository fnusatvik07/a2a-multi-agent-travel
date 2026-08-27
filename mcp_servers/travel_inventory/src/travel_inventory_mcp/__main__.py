"""Run the travel inventory MCP server over streamable HTTP."""

from __future__ import annotations

from atlastrip_core.config import settings
from atlastrip_core.console import get_logger
from atlastrip_core.registry import MCP_PORT

from .server import server


def main() -> None:
    log = get_logger("mcp")
    log.info("travel inventory MCP on http://%s:%d/mcp", settings().host, MCP_PORT)
    server.run("streamable-http", host=settings().host, port=MCP_PORT)


if __name__ == "__main__":
    main()
