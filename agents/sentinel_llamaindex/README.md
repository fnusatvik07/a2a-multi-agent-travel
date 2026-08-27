# Sentinel

Rules on whether a trip may proceed. Evaluates the corporate travel policy and the entry rulebook against an assembled itinerary and returns findings, a compliance verdict, and whether a manager has to sign it off.

**Framework:** LlamaIndex
**Port:** 8003
**Skill:** `screen_trip`

```bash
curl -s http://127.0.0.1:8003/.well-known/agent-card.json | jq
```

## Files

| File | What it does |
|---|---|
| `card.py` | What this agent advertises on its Agent Card |
| `service.py` | The domain logic. Deterministic, no model involved, fully unit tested |
| `agent.py` | The LlamaIndex wiring, where the model actually reasons |
| `executor.py` | The A2A lifecycle, written out in full |
| `__main__.py` | Puts it on a port |

It also has `rules.py`, which is where the binding ruling is made.

## Why LlamaIndex

The travel policy is prose. LlamaIndex indexes the clause text and retrieves what bears on this particular trip, which is exactly what it is for.

## The split that matters

Every clause carries two things. `text` is what a person reads, and the vector index is built from it. `rule` is a small structured description of the same clause, and `rules.py` evaluates it in ordinary Python.

Retrieval decides which clauses are worth **explaining**. The structured rule decides which are **broken**. A traveller should never be stopped, or waved through, because a model paraphrased a paragraph.

## Tests

```bash
agents/sentinel_llamaindex/.venv/bin/python -m pytest tests/agents/sentinel -q
```
