# Architecture

A walk through what actually happens between the moment someone types a
sentence and the moment money moves, and why the pieces are arranged this way.

Read [the README](../README.md) first for the overview. This document is the
detail underneath it.

---

## The two protocols, and the line between them

Almost every multi-agent demo collapses into one process with a long list of
tools. The interesting question is what happens when it cannot: when the agents
belong to different teams, run on different frameworks, and cannot be persuaded
to share a virtualenv.

This project draws the line in one place and holds it:

| | MCP | A2A |
|---|---|---|
| Connects | an agent to its tools | an agent to another agent |
| Unit of work | a tool call, returns immediately | a task, which has a lifecycle |
| Who is in charge | the caller | shared; the callee can pause and ask |
| Failure | an exception | a task state |
| Here | one inventory server, four clients | five agents, one context per trip |

The clearest way to see the difference is the approval. A tool call cannot say
"hold on, I need a human". A task can, by moving to `input-required` and
staying there. That single capability is what makes the network able to model a
real approval chain rather than simulating one.

---

## The trip, node by node

The Concierge is a LangGraph `StateGraph`. The shape of the graph is the shape
of the business process.

```
  START
    │
    ▼
  intake ──────▶ source ──────▶ screen ───┬── not compliant, first time ──┐
                                    ▲     │                                │
                                    │     │                          renegotiate
                                    └─────┴────────────────────────────────┘
                                          │
                                          └── compliant, or already renegotiated
                                                    │
                                                    ▼
                                               authorise ──┬─ approved ──────────┐
                                                           │                     │
                                                           └─ needs approval     │
                                                                  │              │
                                                            await_approval       │
                                                                  │              │
                                                             (interrupt)         │
                                                                  │              │
                                                              confirm ───────────┤
                                                                                 ▼
                                                                            assemble ─▶ END
```

### intake

`agents/concierge_langgraph/src/concierge_langgraph/intake.py`

The only place the Concierge uses a model for anything but prose. A person
writes "the Kaisei QBR in Tokyo from the 14th to the 17th"; the specialists
need an origin, a destination, two ISO dates and a venue id.

LangChain's `with_structured_output` does the conversion against a `ParsedRequest`
model, and it is given the airport list and the customer site list as context so
it resolves names to identifiers rather than inventing them. The result is then
checked against the directory: the employee lookup goes to the MCP server, and a
name that is not in it raises rather than proceeding.

### source

Both specialists are commissioned at once:

```python
flights_reply, stay_reply = await asyncio.gather(
    network.source_flights(flight_brief, state["context_id"]),
    network.source_stay(stay_brief, state["context_id"]),
)
```

Two agents, two processes, two frameworks, one `asyncio.gather`. Neither knows
the other exists. Both calls carry the same context id.

The two briefs are deliberately different in character. Skyline is told the
traveller's grade but not what grade entitles them to. Hearth is told the
nightly cap but not that it is binding.

### screen

Sentinel receives the assembled trip and returns a `ComplianceVerdict`. The
Concierge treats it as binding, without inspecting the policy itself.

Inside Sentinel the work splits in two:

- `rules.py` evaluates the structured `rule` on each clause in ordinary Python
  and produces the findings. This is the ruling, and no model is involved.
- `agent.py` builds a LlamaIndex vector index over the clause `text`, retrieves
  what bears on this trip, and writes the explanation.

Retrieval decides which clauses are worth *explaining*. The structured rule
decides which are *broken*. A traveller should never be stopped, or waved
through, because a model paraphrased a paragraph.

### renegotiate

The part of the design most worth arguing about.

Hearth chose a hotel 210 metres from the customer's office at $298 a night,
against a $280 cap, and said so. Sentinel ruled it a violation of TRV-003.

The Concierge does not overrule either of them. It reads the cap **out of
Sentinel's finding text**:

```python
match = re.search(r"cap of \$([\d,]+(?:\.\d+)?)", finding.detail)
```

and goes back to Hearth with `enforce_cap=True`. Hearth returns a compliant
room 560 metres away. The graph loops back to `screen`, which clears it.

Reading a number back out of prose is not how you would build this at scale;
you would put the cap in a structured field on the finding. It is written this
way on purpose, because it makes the constraint visible: **the Concierge holds
no copy of the policy.** It acts only on what it was told. Swap the policy
document and the orchestrator does not change.

The renegotiation happens exactly once, guarded in `after_screen`. A cap nobody
can meet would otherwise loop between two agents forever.

### authorise, await_approval, confirm

Ledger checks the cost centre. Three outcomes:

- **rejected**: the cost centre cannot cover it, at any level of approval.
- **approved**: committed, with an authorisation code, and a row written to
  `budget_ledger`.
- **needs_approval**: it fits, but policy says a human must sign it off.

On the third, Ledger publishes the verdict as an artifact so the caller has
numbers to put in front of a person, then moves its task to `input-required`
and returns. The task is neither finished nor failed. It is waiting.

The Concierge, holding its own task open for the traveller, sees this and
suspends the graph on a LangGraph `interrupt`. Its executor turns the
suspension into `input-required` on its own A2A task.

The pause has now travelled from the agent that needed the answer, through the
orchestrator, out to the person who can give it, and no agent in that chain
special-cased the others.

When the answer arrives:

1. The traveller's client sends `approve` on the Concierge's task id.
2. The executor resumes the graph with `Command(resume={"approved": True})`.
3. `await_approval` returns the token Ledger handed over when it paused.
4. `confirm` sends it to Ledger **on Ledger's original task id**.
5. Ledger's `execute` runs again, sees the token, commits, and completes.

Two A2A tasks, four turns, one human decision.

### assemble

The itinerary is built from state and handed to a model to write up. The
prompt is given the trip status explicitly, because the compliance findings
describe what the trip *needed* while the budget decision says whether that has
since *happened*, and a summary that tells an approved traveller to go and get
approval is worse than no summary at all.

---

## Why `service.py` and `agent.py` are separate

Every agent has both. The rule is one sentence:

> `service.py` decides. `agent.py` judges and explains.

| Agent | The service decides | The framework agent contributes |
|---|---|---|
| Skyline | which fares are bookable, and the ranking | which of the shortlisted fares to take, and why |
| Hearth | which rooms qualify, and the ranking | which room, and whether the cap was worth breaking |
| Sentinel | which clauses are broken | which clauses to quote, and how to explain them |
| Ledger | whether money moves | the reasoning a manager reads |

Three consequences follow, and all three are load-bearing.

**A model cannot produce an unusable answer.** If Skyline's ADK agent names a
flight that is not on the shortlist, the id is discarded and the top of the
ranking ships. If Hearth's crew invents a hotel, the same. The check is two
lines and it removes an entire category of failure.

**The network survives a bad model turn.** Every framework call is wrapped so
that a timeout, a rate limit, a missing API key or an unparseable answer
degrades to the deterministic path. Nothing takes the network down.

**The whole thing runs offline.** Set `ATLASTRIP_REASONING=deterministic` and
every agent skips its model and calls its own service directly. The A2A traffic,
the MCP calls, the task lifecycle, the interrupt and the database writes are
unchanged. This is what the 87 unit tests use, which is why they run in two
seconds and cost nothing.

---

## Why one virtualenv per service

Not tidiness. A single shared environment cannot exist:

```
crewai 1.15.17     requires openai>=2.30,<3
pydantic-ai 2.35.1 requires openai>=3

google-adk 2.8.0        requires mcp<2
llama-index-tools-mcp   ships against mcp>=2
```

`uv pip install` refuses to resolve them together, correctly. This is not a
contrived constraint invented for the demo; it is the ordinary state of the
Python agent ecosystem in 2026, and it is precisely the situation A2A exists
for. When agents cannot share a process, they can still share a protocol.

The only code all seven environments have in common is `atlastrip-core`, which
holds the pydantic models that define the wire contract, the two storage
adapters, and a few dozen lines of A2A scaffolding. It contains no agent logic
at all.

---

## Storage

**PostgreSQL** holds what is relational and transactional: the inventory, the
people, the cost centres, and the budget ledger that Ledger writes to.

It also holds the A2A task store. Every agent constructs the SDK's
`DatabaseTaskStore` against the same database, so `GetTask` still answers for a
task accepted before the process was last restarted. That matters most for
Ledger, whose tasks can outlive the process while a human thinks.

**TinyDB** holds what reads like documents:

- the policy clauses, which are prose with a structured rule attached
- the entry rulebook
- the customer sites
- the audit trail

The audit trail is one file per writing service. TinyDB keeps its document
index in memory and hands out sequential ids, so two processes writing one file
collide; one file per writer removes the contention, and `audit.trail()` merges
them into a single ordered view on read. This is the only place the demo makes
a concession to TinyDB's single-writer design, and it is called out in
`packages/atlastrip_core/src/atlastrip_core/audit.py`.

---

## Where the protocol details are written down

If you are reading this to learn A2A rather than to understand this codebase,
these are the files worth opening, in order:

1. `packages/atlastrip_core/src/atlastrip_core/a2a_support.py`: building an
   Agent Card, reading a request out of a message, mounting the routes.
2. `agents/skyline_adk/src/skyline_adk/executor.py`: the task lifecycle,
   written out in full. The shortest complete example on the network.
3. `packages/atlastrip_core/src/atlastrip_core/a2a_client.py`: the client side,
   and how a stream of events folds into one reply.
4. `agents/ledger_pydanticai/src/ledger_pydanticai/executor.py`: the interrupt.
5. `agents/concierge_langgraph/src/concierge_langgraph/executor.py`: an agent
   that is a client and a server at the same time, and forwards an interrupt.
6. `tests/network/test_protocol.py`: the wire format, with no client library
   involved at all.

And one detail that costs an hour if you meet it unprepared: the first thing an
executor enqueues must be the `Task` object itself. A status update that
arrives before it is rejected by the client with `Agent should enqueue Task
before TaskStatusUpdateEvent`. That is what `accept_task` is for.
