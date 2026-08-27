# Hearth

Finds somewhere to stay near where the traveller has to be. Weighs proximity to the meeting venue against nightly rate and quality, applies corporate rate agreements, and treats a nightly cap as guidance unless told to enforce it.

**Framework:** CrewAI
**Port:** 8002
**Skill:** `source_stay`

```bash
curl -s http://127.0.0.1:8002/.well-known/agent-card.json | jq
```

## Files

| File | What it does |
|---|---|
| `card.py` | What this agent advertises on its Agent Card |
| `service.py` | The domain logic. Deterministic, no model involved, fully unit tested |
| `agent.py` | The CrewAI wiring, where the model actually reasons |
| `executor.py` | The A2A lifecycle, written out in full |
| `__main__.py` | Puts it on a port |

## Why CrewAI

The one place on this network where a small crew beats a single model. A Scout describes what is genuinely on offer near the venue; a Negotiator makes the call and owns the trade-off. The Negotiator's task declares `output_pydantic`, so CrewAI validates the crew's answer into a typed object before it leaves the process.

## The judgement it is allowed to make

Hearth will go over a nightly cap when proximity justifies it, and flags that it has. Sentinel is the agent that overrules that, and when it does the Concierge comes back with the cap as a hard constraint. That negotiation only exists because judgement and enforcement live in different agents.

## Tests

```bash
agents/hearth_crewai/.venv/bin/python -m pytest tests/agents/hearth -q
```
