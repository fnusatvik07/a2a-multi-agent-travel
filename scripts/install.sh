#!/usr/bin/env bash
# Creates one isolated virtual environment per service.
#
# Every agent here is a separate process with its own dependency tree. They
# never import each other; the only thing they share on the wire is A2A, and
# the only thing they share in code is the small `atlastrip-core` package.
#
# The isolation is not decoration. CrewAI and Pydantic AI pin incompatible
# versions of the openai client, and Google ADK needs an older `mcp` than
# LlamaIndex does, so a single shared environment could not exist even if we
# wanted one. This is what agent interoperability looks like in practice, and
# it is exactly the problem A2A is there to solve.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

CORE="packages/atlastrip_core"

SERVICES=(
  "mcp_servers/travel_inventory"
  "agents/concierge_langgraph"
  "agents/skyline_adk"
  "agents/hearth_crewai"
  "agents/sentinel_llamaindex"
  "agents/ledger_pydanticai"
)

install_into () {
  local service="$1"
  echo "==> $service"
  uv venv --python "$PYTHON_VERSION" --quiet --allow-existing "$service/.venv"
  # The shared package first, always editable, so an edit to a domain model is
  # visible to every service without a reinstall.
  uv pip install --quiet --python "$service/.venv/bin/python" -e "$CORE"
  uv pip install --quiet --python "$service/.venv/bin/python" -e "$service"
  # Each suite runs inside the environment of the thing it tests, so pytest
  # has to be present in every one of them.
  uv pip install --quiet --python "$service/.venv/bin/python" pytest pytest-asyncio
}

install_into "$CORE"
for service in "${SERVICES[@]}"; do
  install_into "$service"
done

# Google ADK still expects the 1.x line of the MCP client library, while
# LlamaIndex has moved to 2.x. Each lives in its own environment, so both are
# satisfied.
uv pip install --quiet --python agents/skyline_adk/.venv/bin/python "mcp>=1.9,<2"

./scripts/_unhide_pth.sh   # see the script for why this is needed on macOS

echo
echo "Environments ready."
echo "Next: make db && make seed"
