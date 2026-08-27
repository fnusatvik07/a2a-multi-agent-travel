# Concierge

The orchestrator. Reads a trip request in plain English, commissions the four specialists over A2A, renegotiates whatever policy rejects, and returns one itinerary. Nothing on its Agent Card says it orchestrates anything; to a caller it is simply an agent that can plan a trip.

**Framework:** LangGraph
**Port:** 8000
**Skill:** `plan_trip`

```bash
curl -s http://127.0.0.1:8000/.well-known/agent-card.json | jq
```

## Files

| File | What it does |
|---|---|
| `card.py` | What this agent advertises on its Agent Card |
| `service.py` | The domain logic. Deterministic, no model involved, fully unit tested |
| `agent.py` | The LangGraph wiring, where the model actually reasons |
| `executor.py` | The A2A lifecycle, written out in full |
| `__main__.py` | Puts it on a port |

It also has `state.py` (what the graph carries), `graph.py` (the state machine), `network.py` (its only capability: asking other agents for things), `intake.py` (free text to a structured request) and `narrative.py` (the write-up).

## Why LangGraph

Booking a trip is a workflow with a fan-out, a compliance gate, one renegotiation and a human interrupt. It is not an open-ended conversation. An explicit `StateGraph` makes that shape visible in the code, and LangGraph's `interrupt` maps one to one onto A2A's `input-required`: when Ledger pauses, the graph suspends, and the executor turns the suspension into an `input-required` status on the Concierge's own task. The pause travels all the way out to the person who can answer it.

## Tests

```bash
agents/concierge_langgraph/.venv/bin/python -m pytest tests/agents/concierge -q
```
