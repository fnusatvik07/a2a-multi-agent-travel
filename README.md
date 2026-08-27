<div align="center">

# AtlasTrip

**Five AI agents. Five different frameworks. Five separate processes.**
**They cannot import each other, so they agree on a protocol instead.**

[![A2A](https://img.shields.io/badge/A2A-spec%201.0-4C51BF?style=for-the-badge)](https://a2a-protocol.org)
[![MCP](https://img.shields.io/badge/MCP-streamable%20HTTP-2C7A7B?style=for-the-badge)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Tests](https://img.shields.io/badge/tests-158%20passing-2F855A?style=for-the-badge)](#tests)
[![License](https://img.shields.io/badge/license-MIT-141413?style=for-the-badge)](LICENSE)

[![LangGraph](https://img.shields.io/badge/Concierge-LangGraph-1C3C3C?logo=langchain&logoColor=white)](agents/concierge_langgraph)
[![Google ADK](https://img.shields.io/badge/Skyline-Google%20ADK-4285F4?logo=google&logoColor=white)](agents/skyline_adk)
[![CrewAI](https://img.shields.io/badge/Hearth-CrewAI-FF5A50?logo=crewai&logoColor=white)](agents/hearth_crewai)
[![LlamaIndex](https://img.shields.io/badge/Sentinel-LlamaIndex-8B5CF6)](agents/sentinel_llamaindex)
[![Pydantic AI](https://img.shields.io/badge/Ledger-Pydantic%20AI-E92063?logo=pydantic&logoColor=white)](agents/ledger_pydanticai)

</div>

<br/>

<p align="center">
  <img src="docs/diagrams/architecture.png" alt="AtlasTrip architecture: a client talks to the Concierge over A2A; the Concierge commissions four specialist agents; all four read one shared MCP server backed by PostgreSQL and TinyDB" width="100%">
</p>

<br/>

Most multi-agent demos are one process with a long list of tools. This one cannot be, and that is the point.

CrewAI pins `openai>=2.30,<3`. Pydantic AI pins `openai>=3`. Google ADK needs `mcp<2`; LlamaIndex has moved to `mcp>=2`. `uv` refuses to resolve them together, correctly. These five agents have no shared runtime available to them, which is the ordinary state of the Python agent ecosystem and exactly the situation **A2A** exists for.

So they run as five independent services and cooperate over the wire:

- **MCP gives an agent its tools.** One inventory server; all four specialists connect to it, each through its own framework's MCP client.
- **A2A lets agents give each other work.** Not a function call, but a task with a lifecycle, which the callee can pause when it needs a human.

They negotiate, they overrule each other, and one of them refuses to spend money without a person. Every number in this repository comes from an actual run.

## Watch it first

<p align="center">
  <a href="https://github.com/fnusatvik07/a2a-multi-agent-travel/raw/main/docs/media/atlastrip-explainer.mp4">
    <img src="docs/media/thumbnail/thumbnail-b.png" alt="Watch the AtlasTrip explainer" width="820">
  </a>
</p>

<p align="center">
  <a href="https://github.com/fnusatvik07/a2a-multi-agent-travel/raw/main/docs/media/atlastrip-explainer.mp4"><b>▶ Watch the explainer</b></a>
  &nbsp;&nbsp;·&nbsp;&nbsp; 2 min 37 &nbsp;&nbsp;·&nbsp;&nbsp; narrated
</p>

A company needs one engineer in Tokyo, which is four separate decisions. Five agents take them. You watch the messages travel, watch one agent refuse a room another had already chosen, and watch a third stop dead rather than spend money without a person.

Every figure on screen comes from a real run. The composition that produced it is in [`videos/atlastrip-a2a-explainer/`](videos/atlastrip-a2a-explainer) and rebuilds with `npx hyperframes render`.

---

## Table of contents

**Start here** &nbsp;·&nbsp; [The scenario](#the-scenario) &nbsp;·&nbsp; [Getting started](#getting-started) &nbsp;·&nbsp; [What a run looks like](#what-a-run-looks-like) &nbsp;·&nbsp; [Building on this](#building-on-this)

**The design** &nbsp;·&nbsp; [The five agents](#the-five-agents) &nbsp;·&nbsp; [How A2A is actually used](#how-a2a-is-actually-used) &nbsp;·&nbsp; [How MCP is actually used](#how-mcp-is-actually-used) &nbsp;·&nbsp; [Why one virtualenv per service](#why-one-virtualenv-per-service) &nbsp;·&nbsp; [Design decisions worth arguing about](#design-decisions-worth-arguing-about)

**Reference** &nbsp;·&nbsp; [Repository layout](#repository-layout) &nbsp;·&nbsp; [The dataset](#the-dataset) &nbsp;·&nbsp; [Running without an API key](#running-without-an-api-key) &nbsp;·&nbsp; [Tests](#tests) &nbsp;·&nbsp; [Troubleshooting](#troubleshooting) &nbsp;·&nbsp; [Versions](#versions)

---

## The scenario

Nimbus Robotics is a fictional company whose travel desk is staffed entirely by agents. An engineer types one sentence:

> Mira Halvorsen needs to be at the Kaisei Robotics quarterly business review in Tokyo from 14 October 2026 to 17 October 2026.

What happens next is not a single model with ten tools. It is five agents with different jobs, different opinions, and a disagreement to resolve.

1. **Concierge** reads the sentence, resolves Mira in the directory, and commissions two agents at once.
2. **Skyline** searches live fare inventory. The flight is eleven hours, so it offers premium economy where the fare is within a defensible multiple of economy. It does not know whether Mira is *allowed* premium economy, and says so on its own agent card.
3. **Hearth** searches lodging. The nearest hotel to the customer's office is $298 a night against a $280 cap. Hearth takes it anyway, because it is 210 metres from the front door, and flags that it went over.
4. **Sentinel** screens the assembled trip against the corporate travel policy and the entry rulebook. It rules the hotel a violation of clause TRV-003 and states the cap in its finding.
5. **Concierge** does not overrule anybody. It goes back to Hearth with the cap as a hard constraint. Hearth returns a compliant room 560 metres away. Sentinel screens again and clears it.
6. **Ledger** checks the cost centre. The trip fits the remaining budget but is over the $3,000 auto-approval threshold, so it moves its A2A task into `input-required` and stops.
7. That pause **propagates**. The Concierge's own task goes to `input-required` too, and the person who asked for the trip sees the question.
8. On approval, both tasks resume where they left off, Ledger commits the money to Postgres, and the itinerary is written.

The interesting part is step 5. Hearth made a defensible judgement, Sentinel overruled it, and the network resolved the disagreement by negotiating rather than by one agent quietly knowing better. That only works because judgement and enforcement live in different agents that can talk to each other.

<p align="center">
  <img src="docs/diagrams/trip-sequence.png" alt="Sequence diagram of one trip: the Concierge commissions Skyline and Hearth in parallel, Sentinel refuses the room, the Concierge re-asks Hearth, and Ledger pauses for a human" width="100%">
</p>

---

## Getting started

Everything below was run from a clean clone before it was written down.

### 1. What you need

| | | |
|---|---|---|
| **Python 3.11+** | for the services | `python3 --version` |
| **[uv](https://docs.astral.sh/uv/getting-started/installation/)** | builds the seven virtualenvs | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | runs PostgreSQL, nothing else | `docker info` |
| **An OpenAI API key** | the agents' reasoning | [platform.openai.com](https://platform.openai.com/api-keys) |

No key? The network still runs. Skip to [running without an API key](#running-without-an-api-key).

### 2. Set it up

```bash
git clone https://github.com/fnusatvik07/a2a-multi-agent-travel.git
cd a2a-multi-agent-travel

cp .env.example .env
$EDITOR .env                  # put your key in OPENAI_API_KEY

make install                  # seven virtualenvs, one per service
make db                       # PostgreSQL in Docker, on port 5433
make seed                     # 1,938 flights, 6,042 hotel rates, the policy book
```

`make install` takes two or three minutes the first time and a few seconds after
that, because `uv` caches aggressively. It builds a separate environment for
every service on purpose; see [why one virtualenv per service](#why-one-virtualenv-per-service).

### 3. Run it

```bash
make run                      # the MCP server and all five agents
```

Leave that running. It prints each agent's card URL and holds the terminal;
Ctrl-C stops everything. Then in a **second terminal**:

```bash
make doctor                   # confirm all seven services are up
make demo                     # plan the sample trip
```

`make demo` will stop and ask you to approve a spend, because one of the agents
refuses to commit money without a person. That pause is the most interesting
thing in the project, so answer it yourself the first time. `make demo-yes`
approves without prompting, for scripts and CI.

### 4. Look around

```bash
make cards                    # every agent's card, as A2A discovery returns it
make trail                    # replay what actually crossed the wire
make plan REQUEST="Deshawn Okafor needs three days in London next month"
make test                     # 88 unit tests offline, 70 against the live network
make lint                     # ruff over every service
```

`make` on its own lists every target with a one-line description.

### If something goes wrong

`make doctor` first: it checks PostgreSQL, the MCP server and all five agents
separately, so you learn which piece is unhappy before reading any logs. Agent
logs are in `logs/`. The [troubleshooting section](#troubleshooting) covers the
failures people actually hit.

---

## Building on this

The repository is laid out so you can take one piece without taking the rest.

**To add a sixth agent**, copy the folder of whichever existing agent is closest
in shape. Every agent is the same five files:

```
agents/<name>/src/<pkg>/
    card.py        what it advertises on its Agent Card
    service.py     the domain logic. Deterministic, no model, unit tested
    agent.py       the framework wiring, where the model reasons
    executor.py    the A2A lifecycle, written out in full
    __main__.py    puts it on a port
```

Add it to `packages/atlastrip_core/src/atlastrip_core/registry.py`, give it a
port, and it is discoverable. Nothing else needs to know it exists.

**To swap a framework**, only `agent.py` changes. `service.py`, `executor.py`
and the Agent Card are framework-agnostic by construction, which is the whole
argument the project is making.

**To change the domain**, the travel logic lives in the four `service.py` files,
the data lives in `data/seed/` as editable JSON, and the policy book is ten
documents in `data/seed/policies.json`. Nothing about A2A or MCP cares that this
is travel.

**To reuse just the A2A plumbing**, take
`packages/atlastrip_core/src/atlastrip_core/` - about 1,000 lines covering Agent
Card construction, the client, the task store, and a dependency-free MCP client
written against the wire format.

### What this is and is not

It is a **working reference implementation** of A2A with real framework
integrations, a real dataset, and a test suite that pins the behaviour down. If
you are evaluating A2A, or learning it, or want a shape to copy, it is meant
for exactly that.

It is **not production infrastructure.** Before you ship anything resembling it:

- The approval token is a correlation id, not a credential. Ledger derives it
  from the trip and the amount so a replay cannot mint a second one, but there
  is no signature and no identity provider. Real approvals need a signed grant.
- The Agent Cards advertise no `securitySchemes`. Every agent trusts every
  caller. A2A supports API keys, HTTP auth, OAuth2 and mTLS; none is wired up.
- The LangGraph checkpointer is in memory, so a Concierge restart loses trips
  that are mid-approval. The A2A task in PostgreSQL survives; the graph state
  does not. Swap `MemorySaver` for the PostgreSQL checkpointer to fix it.
- Agents talk over plain HTTP on localhost. There is no TLS and no service mesh.
- There is no rate limiting, no retry policy and no circuit breaker between
  agents. One slow specialist blocks its caller until the timeout.

None of those are hard to add. They are left out because each one would have
obscured the thing the project is trying to show.

---

## What a run looks like

This is real output, trimmed only for width.

```
──────────────────────────────────────────────────────────────────────────────
The network at work
  · Planning TRIP-990D73F8.
  · Understood: Mira Halvorsen (IC5), SFO to HND, 2026-10-14 to 2026-10-17.
  · Skyline: UA 837 / UA 838 in premium economy, $3,110.48.
  · Hearth: Shinagawa Bay Tower, $298.33 a night, $894.99.
  · Sentinel: This trip cannot proceed as booked because the lodging cost
    exceeds the Tokyo nightly cap and the total is above the auto-approval
    threshold.
  · violation: TRV-003 Shinagawa Bay Tower is $298.33 a night against a Tokyo
    cap of $280.00, an overage of $18.33 a night ($54.99 across 3 nights).
  · warning: TRV-005 Trip total $4,013.87 is at or above the $3,000.00
    auto-approval threshold.
  · Re-asked Hearth with the $280.00 cap enforced: Konan Garden Hotel,
    $189.96 a night, $569.88.
  · Sentinel: Your trip to Tokyo is within policy and can proceed once your
    manager approves it.
  · Ledger: needs_approval. The requested trip costs $3,688.76, and the cost
    centre currently has $7,600.00 remaining for the quarter.

──────────────────────────────────────────────────────────────────────────────
Approval required
  Approve $3,688.76 against CC-ROBOTICS-APAC?
  This needs elena.marchetti@nimbusrobotics.example.

  Approve this spend? [y/N] y

──────────────────────────────────────────────────────────────────────────────
Resumed
  · Approval received. Returning to Ledger.
  · Ledger: approved. This leaves $3,911.24 remaining in the quarterly budget.
  · Itinerary confirmed, $3,688.76.

──────────────────────────────────────────────────────────────────────────────
TRIP-990D73F8  CONFIRMED
  flights   UA 837 SFO-HND 14 Oct 17:55Z, UA 838 back 17 Oct 06:30Z
            premium economy, $3,110.48
  stay      Konan Garden Hotel (3*), 0.56 km from the venue
            3 nights at $189.96, $569.88
  warning   TRV-005 Trip authorisation threshold
  info      TRV-010 Entry documentation
  approved  AUTH-351693FF2A, $3,911.24 left in CC-ROBOTICS-APAC
  total     $3,688.76
```

`make trail` then replays the same run as protocol traffic:

```
  17:56:15  concierge   inbound    received   Mira Halvorsen needs to be at ...
  17:56:17  concierge   outbound   asked      concierge -> skyline
  17:56:17  concierge   outbound   asked      concierge -> hearth
  17:56:25  hearth      inbound    completed  Shinagawa Bay Tower $894.99
  17:56:31  skyline     inbound    completed  $3,110.48 round trip
  17:56:42  sentinel    inbound    completed  cannot proceed as booked ...
  17:56:42  concierge   outbound   asked      concierge -> hearth
  17:56:48  hearth      inbound    completed  Konan Garden Hotel $569.88
  17:56:57  sentinel    inbound    completed  within policy, approval needed
  17:57:00  ledger      inbound    escalated  awaiting approval for $3,688.76
  17:57:00  concierge   inbound    escalated  Approve $3,688.76 ...
```

Every line is one A2A exchange, and every line carries the same context id.

---

## The five agents

| Agent | Framework | Job | Why that framework |
|---|---|---|---|
| **Concierge** `:8000` | LangGraph | Orchestrates the trip and talks to the traveller | Booking a trip is a workflow with a fan-out, a compliance gate and a human interrupt, not an open-ended chat. An explicit `StateGraph` makes that shape visible, and LangGraph's `interrupt` maps one-to-one onto A2A's `input-required`. |
| **Skyline** `:8001` | Google ADK | Sources and ranks flights | ADK's `McpToolset` connects an agent to an MCP server in three lines, so the model can browse the live timetable itself rather than being handed a fixed list. |
| **Hearth** `:8002` | CrewAI | Sources lodging | The one place where a small crew beats a single model: a Scout describes what is on offer, a Negotiator makes the call and owns the trade-off. `output_pydantic` validates the crew's answer before it leaves. |
| **Sentinel** `:8003` | LlamaIndex | Rules on policy and entry requirements | The travel policy is prose. LlamaIndex indexes the clause text and retrieves what bears on this trip, which is exactly what it is for. |
| **Ledger** `:8004` | Pydantic AI | Authorises spend against a cost centre | A typed answer, enforced by the framework. `output_type=SpendOpinion` means the model cannot return an essay where a decision was asked for. |

Every agent has the same four files, so once you have read one you can read any of them:

```
agents/<name>/src/<pkg>/
    card.py        what the agent advertises on its Agent Card
    service.py     the domain logic, deterministic, no model involved
    agent.py       the framework wiring, where the model actually reasons
    executor.py    the A2A lifecycle, written out in full
    __main__.py    put it on a port
```

### The split between `service.py` and `agent.py`

This is the most important design decision in the repository, so it is worth stating plainly.

**`service.py` decides. `agent.py` judges and explains.**

- Skyline's service ranks fares and assembles the proposal. Its ADK agent chooses one from the shortlist. If the model names a flight that does not exist, the choice is discarded and the ranking ships. A model can have an opinion; it cannot quote an unbookable itinerary.
- Sentinel's `rules.py` evaluates the structured half of each policy clause in ordinary Python. That ruling is binding. Its LlamaIndex agent retrieves the clause text and writes the explanation. A traveller is never stopped, or waved through, because a model paraphrased a paragraph.
- Ledger's service decides whether money moves and writes the commitment. Its Pydantic AI agent writes the reasoning a manager reads. An optimistic model cannot spend anything.

Every framework call is wrapped so that a failure, a missing API key or an unusable answer degrades to the deterministic path instead of taking the network down.

---

## How A2A is actually used

Not a checklist of features, but what the protocol is doing here and where to read it.

### Agent Cards, and discovery

Every agent serves a card at `/.well-known/agent-card.json`. It is the only thing a caller needs: the interface list gives the transports and URLs, the skill list gives the operations.

```bash
curl -s http://127.0.0.1:8001/.well-known/agent-card.json | jq
```

Nothing on the Concierge's card says "this one orchestrates the others". To a caller it is simply an agent that can plan a trip. Read `packages/atlastrip_core/src/atlastrip_core/a2a_support.py` for how a card is built, and any agent's `card.py` for what goes on it.

### The task lifecycle

A2A models work as a task with a state, not as a request and a response. Every executor in this repository walks the same path, written out in full rather than hidden behind a base class.

<p align="center">
  <img src="docs/diagrams/task-lifecycle.png" alt="The A2A task lifecycle: submitted, working, and input-required across the top; rejected, failed, completed and canceled as terminal states" width="100%">
</p>

One detail worth knowing before you write your own: **the first thing enqueued must be the `Task` object itself.** A status update that arrives before it is rejected by the client. That is what `accept_task` exists for.

Read `agents/skyline_adk/src/skyline_adk/executor.py` for the shortest complete example.

### Structured artifacts

Agents here exchange validated JSON, not prose. Each result is published as an A2A `DataPart` alongside a text part written for a human, so one message serves both the machine and the person watching.

The shapes live in one shared package, `atlastrip_core.models`. Those pydantic models are the whole contract between the agents. They share nothing else.

### One context id per trip

Every call the Concierge makes carries the same `contextId`. Five processes, one conversation, and an audit trail that reads as a single story. That is what `make trail` prints.

### Interrupting, and resuming

Ledger cannot approve a $3,688 trip on its own. Rather than failing, it moves the task to `input-required` and returns. The task is not finished; it is waiting.

The Concierge, holding its own task open for the traveller, sees the pause and moves *its* task to `input-required` too. The interruption travels from the agent that needs the answer, through the orchestrator, out to the person who can give it. No agent in that chain special-cases the others.

On approval, a second message is sent **on the same task id**, the executor runs again with the token present, and the task completes.

- `agents/ledger_pydanticai/src/ledger_pydanticai/executor.py` raises the pause
- `agents/concierge_langgraph/src/concierge_langgraph/executor.py` forwards it
- `tests/network/test_specialists.py::test_the_approval_settles_the_same_task` pins it down

### Task state in Postgres

Every agent uses the SDK's `DatabaseTaskStore` against the same Postgres database, so `GetTask` still answers for a task accepted before the process was last restarted. This matters most for Ledger, whose tasks can outlive the process while a human thinks about them.

### Version negotiation, and the method names

A2A 1.0 renamed the JSON-RPC methods to match the gRPC service. `SendMessage`, not `message/send`. Most material written before the 1.0 spec shows the old names.

These agents enable compatibility mode, so both spellings work. The catch, which costs an hour if you meet it unprepared: **with compatibility enabled, a request that does not send an `A2A-Version: 1.0` header is treated as 0.3.**

```bash
curl -s http://127.0.0.1:8001/a2a/jsonrpc \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'A2A-Version: 1.0' \
  -d '{"jsonrpc":"2.0","id":1,"method":"GetTask","params":{"id":"..."}}'
```

`tests/network/test_protocol.py` exercises all of this with no client library at all, so the repository shows the wire format and not just the Python wrapper.

---

## How MCP is actually used

One MCP server, `mcp_servers/travel_inventory`, holds every tool that touches data:

| Tool | Returns |
|---|---|
| `search_flights` | Bookable fares for a city pair on one local departure date |
| `search_hotels` | Rooms in a city, with distance to a customer site |
| `get_ground_transport` | Airport transfer options |
| `lookup_employee` | Grade, passport, cost centre, manager |
| `lookup_venue` | A customer site and its coordinates |
| `get_cost_center_budget` | Allowance, committed, remaining |
| `record_commitment` | Writes money to the ledger |
| `list_airports` | The airports with inventory |

All four specialists read that one server, each through its own framework's MCP client:

```python
# Google ADK
McpToolset(connection_params=StreamableHTTPConnectionParams(url=MCP_URL))

# CrewAI
MCPServerAdapter({"url": MCP_URL, "transport": "streamable-http"})

# LlamaIndex
McpToolSpec(client=BasicMCPClient(MCP_URL))

# Pydantic AI
MCPToolset(MCP_URL)
```

Because the tools live outside every agent, swapping a framework never means rewriting a tool.

There is also a fifth client: `packages/atlastrip_core/src/atlastrip_core/mcp_http.py`, about 150 lines of `httpx` that speaks the streamable HTTP transport directly. It exists for a practical reason and a pedagogical one. The practical reason is that the four frameworks pin three mutually incompatible versions of the `mcp` package, and shared code cannot join that argument. The pedagogical one is that MCP is a small protocol, and seeing it unwrapped is more useful than seeing it wrapped:

1. `POST` an `initialize` request; the response header carries a session id
2. `POST` a `notifications/initialized` notification
3. `POST` `tools/call` for as long as you like

---

## Repository layout

```
a2a-multi-agent-travel/
├── agents/
│   ├── concierge_langgraph/     the orchestrator
│   ├── skyline_adk/             flights
│   ├── hearth_crewai/           lodging
│   ├── sentinel_llamaindex/     policy and entry rules
│   └── ledger_pydanticai/       budget and approvals
├── mcp_servers/
│   └── travel_inventory/        the one MCP server everyone reads
├── packages/
│   └── atlastrip_core/          the only shared code: models, storage, A2A glue
├── data/
│   ├── seed/                    the dataset, as editable JSON
│   └── tinydb/                  policy documents and the audit trail
├── scripts/
│   ├── install.sh               one virtualenv per service
│   ├── seed_data.py             build the dataset
│   ├── run_network.sh           start everything
│   ├── run_tests.sh             each suite in its own environment
│   └── atlastrip.py             the CLI
├── tests/
│   ├── core/                    the shared package
│   ├── agents/                  one suite per agent, run in its own venv
│   └── network/                 integration, against the running network
└── docs/
    ├── ARCHITECTURE.md          the deeper walk-through
    ├── DATASET.md               what is in the data and how to change it
    └── diagrams/                draw.io sources and rendered SVGs
```

### Why one virtualenv per service

Not for tidiness. Because a single shared environment **cannot exist**:

- CrewAI needs `openai<3`; Pydantic AI needs `openai>=3`
- Google ADK needs `mcp<2`; LlamaIndex has moved to `mcp>=2`

`uv pip install` refuses to resolve them together, and it is right to. This is exactly the situation A2A exists for: when agents cannot share a process, they can still share a protocol. `scripts/install.sh` builds seven environments in about two minutes.

---

## The dataset

Hand-authored where a person should be able to read and edit it, generated where volume is needed. Everything is seeded, so two runs produce identical output.

**PostgreSQL** holds what is relational:

| Table | Rows | Notes |
|---|---|---|
| `flights` | 1,938 | 5 routes, real carriers, 2 to 3 fare products per cabin per day |
| `hotel_rates` | 6,042 | 19 hotels, 3 room types, every night from September to December 2026 |
| `hotels` | 19 | Tokyo, London, Singapore, San Francisco, New York, with coordinates |
| `employees` | 6 | Grade, passport country, cost centre, manager |
| `cost_centers` | 4 | Quarterly budget |
| `budget_ledger` | 11 | Opening commitments, so budgets are already partly spent |
| `airports`, `ground_transport` | 23 | |
| `a2a_tasks` | live | Created and owned by the A2A SDK |

**TinyDB** holds what reads like documents:

- `policies.json`: 10 travel policy clauses. Each carries `text` (prose, which Sentinel's vector index is built from) and `rule` (a structured description of the same clause, which `rules.py` evaluates). Retrieval decides which clauses are worth *explaining*; the structured rule decides which are *broken*.
- `visa_rules.json`: 12 passport and destination pairs with processing times.
- `venues.json`: 5 customer sites with coordinates, so lodging can be ranked by walking distance.
- `audit_<service>.json`: the runtime trail. One file per writer, because TinyDB hands out sequential document ids in memory and two processes writing one file will collide.

Edit anything in `data/seed/` and run `make seed`. See [docs/DATASET.md](docs/DATASET.md).

The scenario is tuned so the interesting things happen: the nearest Tokyo hotel is $298 against a $280 cap, and the trip lands at $3,689 against a $3,000 approval threshold with $7,600 left in the quarter. Change `data/seed/hotels.json` or `data/seed/policies.json` and the negotiation changes with it.

---

## Running without an API key

Set `ATLASTRIP_REASONING=deterministic` in `.env`. Every agent then skips its model and runs its own `service.py` directly. The A2A traffic, the MCP calls, the task lifecycle, the interrupt and the database writes are all unchanged; only the judgement and the prose are gone.

This is what the unit tests use, which is why they run offline and for free.

The one thing that needs a model is the Concierge's intake, since something has to turn a sentence into two ISO dates. In deterministic mode it falls back to a crude parser that recognises a city name and assumes a three night trip four weeks out.

---

## Tests

```bash
make test          # everything: 158 tests
make test-unit     # 88 tests, offline, no API key, about 2 seconds
make test-network  # 70 tests against the running network, about 4 minutes
```

There is no single pytest run, because there is no environment that can import all five agents at once. `scripts/run_tests.sh` runs each suite inside the virtualenv of the thing it tests. The integration suite skips itself with a clear message when the network is not up.

What the integration tests actually assert:

- every card is reachable, advertises its skill and offers both HTTP bindings
- a task walks submitted, working, artifact, completed
- a malformed brief is `rejected` (the caller was wrong), an empty route is `failed` (the work could not be done)
- the raw JSON-RPC binding answers with no client library present, in both 1.0 and 0.3 spellings
- Hearth never exceeds the cap when told to enforce it, and relaxing the cap never moves the traveller further from the venue
- Sentinel breaks TRV-003 on an over-cap room, and states the cap in the finding
- Ledger pauses, and the approval settles the same task id
- one sentence produces a confirmed itinerary, with all five agents in the trail and Hearth asked twice
- declining the approval leaves the ledger untouched

The network suite restores the seeded budget ledger at session start and removes its own commitments after each test, so runs do not drift.

---

## Design decisions worth arguing about

Honest notes on the choices a reader might push back on.

**The Concierge is not a policy engine.** It passes the nightly cap to Hearth as guidance and lets Hearth exceed it, then acts on Sentinel's ruling. A simpler design would have the orchestrator enforce the cap up front and skip a round trip. That design has no negotiation in it, and negotiation between independently-owned agents is the thing worth demonstrating. The Concierge reads the cap back out of Sentinel's finding text rather than holding a copy of the policy.

**The renegotiation happens exactly once.** A cap nobody can meet would otherwise loop between two agents forever. See `graph.after_screen`.

**The approval token is a correlation id, not a credential.** Ledger derives it from the trip and the amount, so replaying an authorisation cannot mint a second one and re-costing the trip invalidates the old approval. It is not a security boundary. In production this would be a signed grant from an identity provider, and Ledger would verify the signature.

**The LangGraph checkpointer is in memory.** Restart the Concierge mid-approval and the graph state is gone, though the A2A task in Postgres survives. Swapping `MemorySaver` for the Postgres checkpointer would fix it; it is left simple because the checkpointer is not what the project is about.

**Every model call can fail without consequence.** That is deliberate, and it is why the split between `service.py` and `agent.py` exists. It also means you can watch the network run correctly with the API key removed, which is a useful thing to be able to demonstrate.

**Integration tests assert invariants, not choices.** Two of them used to name the hotel they expected Hearth to pick. It usually picked it, and they usually passed. A model that is genuinely exercising judgement will not always choose the same thing, so those tests now assert what must always hold: that an enforced cap is never exceeded, and that relaxing a cap never moves the traveller further away. `tests/network/test_specialists.py` says so in its own comments.

**Hearth's ranking uses real units, not normalised scores.** An earlier version min-max normalised price, distance and stars. A test caught that this is scale-blind: it would pay $900 a night to save 400 metres, because it only ever saw "most expensive" and "nearest" rather than how much more and how much nearer. The ranking now scores price as a premium over the cheapest room and distance in kilometres. `tests/agents/hearth/test_ranking.py` keeps it honest.

---

## Troubleshooting

**`make doctor` says an agent is down.** Look in `logs/<agent>.log`. The most common cause on a first run is that `make db` and `make seed` have not been run.

**`Method not found` from a `curl` against an agent.** You are probably sending `message/send` without an `A2A-Version` header, or `SendMessage` with one pointed at 0.3. See [version negotiation](#version-negotiation-and-the-method-names).

**`Agent should enqueue Task before TaskStatusUpdateEvent`.** Your executor published a status update before the `Task` object. Call `accept_task` first.

**Port already in use.** The agents use 8000 to 8004, and the MCP server uses 8100. Postgres is on 5433 rather than 5432 so it never collides with a local install. Change the ports in `packages/atlastrip_core/src/atlastrip_core/registry.py`.

**Ledger rejects everything.** The cost centre budget has been spent by earlier runs. `make reset` puts the dataset back.

**`ModuleNotFoundError: atlastrip_core`, in every environment at once, on macOS.** Editable installs work through a `.pth` file in `site-packages`, and CPython's `site.py` silently skips any `.pth` file carrying the macOS `hidden` flag. Some setups set that flag on dot-prefixed files: iCloud Desktop and Documents sync does it, and so do several endpoint management agents.

Diagnose it with `ls -lO <venv>/lib/python3.12/site-packages/*.pth`. The flag column reads `hidden` when this has happened. Clear it with:

```bash
./scripts/_unhide_pth.sh
```

Every entry point already does this for you, and the `make` targets and run scripts additionally set `PYTHONPATH` so the imports work even if the flag comes back mid-run. If you invoke a virtualenv's Python directly and hit this, go through `make` instead.

---

## Versions

Pinned and verified against these, in August 2026:

| | |
|---|---|
| `a2a-sdk` | 1.1.2, implementing A2A spec 1.0 with 0.3 compatibility |
| `mcp` | 2.1.1 server side, 1.x and 2.x clients depending on the framework |
| `google-adk` | 2.8.0 |
| `crewai` | 1.15.17 |
| `langgraph` / `langchain` | 1.2.11 / 1.3.17 |
| `llama-index-core` | 0.14.24 |
| `pydantic-ai-slim` | 2.35.1 |
| Python | 3.12 |
| Model | `gpt-4.1-mini` by default, the same for all five agents |

All five agents deliberately use the same model, so any behavioural difference you see between them comes from the framework rather than the model. Change `ATLASTRIP_MODEL` in `.env` to use another.

---

## Further reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): the walk-through, node by node
- [docs/DATASET.md](docs/DATASET.md): what is in the data and how to change it
- [docs/diagrams/](docs/diagrams/): draw.io sources, and how to regenerate them
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [a2a-python SDK](https://github.com/a2aproject/a2a-python)
- [Model Context Protocol](https://modelcontextprotocol.io)

## License

MIT. See [LICENSE](LICENSE).
