#!/usr/bin/env bash
# Starts the MCP server and all five agents, each from its own virtualenv.
#
# Logs go to logs/<service>.log. Ctrl-C stops everything.
set -euo pipefail

cd "$(dirname "$0")/.."
./scripts/_unhide_pth.sh
mkdir -p logs

declare -a PIDS=()

CORE_SRC="$PWD/packages/atlastrip_core/src"

start () {
  local name="$1" venv="$2" module="$3" src="$4"
  # PYTHONPATH is belt and braces; the editable installs already cover this.
  # See scripts/_unhide_pth.sh for the macOS case where they stop working.
  PYTHONPATH="$CORE_SRC:$PWD/$src" \
    "$venv/bin/python" -m "$module" > "logs/$name.log" 2>&1 &
  PIDS+=($!)
  printf '  %-12s pid %-7s logs/%s.log\n' "$name" "$!" "$name"
}

stop () {
  echo
  echo "Stopping the network."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop EXIT INT TERM

echo "Starting the AtlasTrip network."
start inventory-mcp mcp_servers/travel_inventory/.venv travel_inventory_mcp mcp_servers/travel_inventory/src
start skyline       agents/skyline_adk/.venv           skyline_adk          agents/skyline_adk/src
start hearth        agents/hearth_crewai/.venv         hearth_crewai        agents/hearth_crewai/src
start sentinel      agents/sentinel_llamaindex/.venv   sentinel_llamaindex  agents/sentinel_llamaindex/src
start ledger        agents/ledger_pydanticai/.venv     ledger_pydanticai    agents/ledger_pydanticai/src
start concierge     agents/concierge_langgraph/.venv   concierge_langgraph  agents/concierge_langgraph/src

echo
echo -n "Waiting for the agents to come up"
for _ in $(seq 1 60); do
  if curl -fsS -m 2 http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
  && curl -fsS -m 2 http://127.0.0.1:8001/healthz >/dev/null 2>&1 \
  && curl -fsS -m 2 http://127.0.0.1:8002/healthz >/dev/null 2>&1 \
  && curl -fsS -m 2 http://127.0.0.1:8003/healthz >/dev/null 2>&1 \
  && curl -fsS -m 2 http://127.0.0.1:8004/healthz >/dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

cat <<'BANNER'

  Concierge   http://127.0.0.1:8000/.well-known/agent-card.json   LangGraph
  Skyline     http://127.0.0.1:8001/.well-known/agent-card.json   Google ADK
  Hearth      http://127.0.0.1:8002/.well-known/agent-card.json   CrewAI
  Sentinel    http://127.0.0.1:8003/.well-known/agent-card.json   LlamaIndex
  Ledger      http://127.0.0.1:8004/.well-known/agent-card.json   Pydantic AI
  Inventory   http://127.0.0.1:8100/mcp                           MCP

  In another terminal:  make demo

BANNER

wait
