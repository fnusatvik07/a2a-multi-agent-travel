# Skyline

Sources and ranks air travel. Reads live fare inventory and returns one recommended outbound and return flight with alternatives. It does not rule on whether the traveller is allowed that cabin or that carrier, and says so on its card.

**Framework:** Google ADK
**Port:** 8001
**Skill:** `source_flights`

```bash
curl -s http://127.0.0.1:8001/.well-known/agent-card.json | jq
```

## Files

| File | What it does |
|---|---|
| `card.py` | What this agent advertises on its Agent Card |
| `service.py` | The domain logic. Deterministic, no model involved, fully unit tested |
| `agent.py` | The Google ADK wiring, where the model actually reasons |
| `executor.py` | The A2A lifecycle, written out in full |
| `__main__.py` | Puts it on a port |

## Why Google ADK

ADK's `McpToolset` connects an agent to an MCP server in three lines, so the model can browse the wider timetable itself rather than being handed a fixed list.

ADK will not combine a strict `output_schema` with tools, so rather than give up the tools the reply is parsed leniently and falls back to the deterministic ranking whenever the answer is missing, malformed, or names a flight that does not exist. A model is allowed to have an opinion here; it is not allowed to quote an unbookable itinerary.

## Tests

```bash
agents/skyline_adk/.venv/bin/python -m pytest tests/agents/skyline -q
```
