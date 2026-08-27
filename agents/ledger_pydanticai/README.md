# Ledger

Authorises travel spend against a cost centre. Checks the live budget position, approves what it can, and interrupts the task when a human has to sign off. The only agent on the network that changes anything.

**Framework:** Pydantic AI
**Port:** 8004
**Skill:** `authorize_spend`

```bash
curl -s http://127.0.0.1:8004/.well-known/agent-card.json | jq
```

## Files

| File | What it does |
|---|---|
| `card.py` | What this agent advertises on its Agent Card |
| `service.py` | The domain logic. Deterministic, no model involved, fully unit tested |
| `agent.py` | The Pydantic AI wiring, where the model actually reasons |
| `executor.py` | The A2A lifecycle, written out in full |
| `__main__.py` | Puts it on a port |

## Why Pydantic AI

A typed answer, enforced by the framework. `output_type=SpendOpinion` means the model cannot return an essay where a decision was asked for, and the result arrives already validated.

## The interrupt

Most A2A tasks run start to finish. This one does not. When policy says a human must approve the spend, Ledger publishes the verdict as an artifact so the caller has numbers to show someone, then moves the task to `input-required` and returns. The task is neither finished nor failed; it is waiting.

The caller gets the approval and sends a second message **on the same task id**. `execute` runs again with the token present, the money is committed, and the task completes.

## What the model is not allowed to do

`service.assess` has already decided by the time the model is asked anything. The opinion it writes is the reasoning a manager reads. It cannot move money, and it cannot loosen the outcome.

## Tests

```bash
agents/ledger_pydanticai/.venv/bin/python -m pytest tests/agents/ledger -q
```
