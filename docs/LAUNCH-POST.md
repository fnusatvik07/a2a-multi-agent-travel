# Skool launch post

---

**I built a multi-agent system where the agents literally cannot import each other.**

Most multi-agent demos are one Python process with a long list of tools. I wanted to know what happens when that isn't possible, because in real companies it usually isn't. Different teams, different frameworks, different release cycles.

So I built AtlasTrip: a corporate travel desk staffed by five AI agents, each on a different framework.

- **Concierge** on LangGraph, orchestrates
- **Skyline** on Google ADK, sources flights
- **Hearth** on CrewAI, finds lodging
- **Sentinel** on LlamaIndex, rules on travel policy
- **Ledger** on Pydantic AI, controls the money

Here's the thing that makes it real rather than a toy: **these five genuinely cannot share a Python process.** CrewAI pins `openai<3`. Pydantic AI pins `openai>=3`. Google ADK needs `mcp<2`, LlamaIndex has moved to `mcp>=2`. `uv` refuses to resolve them together, and it's right to.

That is the ordinary state of the Python agent ecosystem right now. And it is exactly the problem the **A2A protocol** exists to solve.

So they don't share a process. They share two protocols:

- **MCP** gives an agent its tools. One inventory server, four different framework clients reading it.
- **A2A** lets agents give each other work. Not a function call, a task with a lifecycle that the receiver can pause.

**Two moments from a real run that a single-process agent can't produce:**

**1. They disagree, and negotiate.** Hearth picks a hotel $18 over the policy cap because it's 210 metres from the customer's door, and says so. Sentinel overrules it. The orchestrator does not pick a side. It goes back to Hearth and asks again with the cap as a hard limit. Judgement and enforcement live in different agents, so they have to actually talk.

**2. One of them refuses to spend money.** Ledger will not commit $3,688 without a human. It moves its task to `input-required` and stops. Not fails, stops. And that pause propagates: the orchestrator pauses too, so the question reaches the person who can answer it. Then both resume exactly where they stopped.

**What's in the repo**

- 5 agent services, 1 MCP server, 7 isolated virtualenvs
- A seeded dataset: 1,938 flights, 6,042 hotel rates, a 10-clause policy book
- 158 tests. 88 run offline with no API key at all
- Architecture diagrams, and a 2m37 explainer video
- MIT licensed

Clone it, add an OpenAI key, `make install && make db && make seed && make run`. It works.

I've also written down what it *isn't*, in the README: no auth on the agent cards, the approval token is a correlation id rather than a credential, the graph checkpointer is in memory. It's a reference implementation, not production infrastructure, and I'd rather say that than have someone find out the hard way.

👉 **https://github.com/fnusatvik07/a2a-multi-agent-travel**

Happy to answer anything about the A2A bits. The interrupt propagation was the part I found most interesting to build.

---

# Shorter version (X / LinkedIn)

---

I built a multi-agent system where the agents literally cannot import each other.

Five AI agents, five frameworks: LangGraph, Google ADK, CrewAI, LlamaIndex, Pydantic AI.

They can't share a Python process. CrewAI pins openai<3, Pydantic AI pins openai>=3. Google ADK needs mcp<2, LlamaIndex needs mcp>=2. uv refuses to resolve them, correctly.

That's the ordinary state of the ecosystem, and it's exactly what A2A is for.

So they run as five services and talk over the wire. MCP gives an agent its tools. A2A lets agents give each other work: not a call, a task the receiver can pause.

Two things a single-process agent can't do:

→ They disagree. One picks a hotel $18 over policy because it's 210m from the customer's door. Another overrules it. The orchestrator doesn't pick a side, it asks again with the cap enforced.

→ One refuses to spend $3,688 without a human. It pauses its task, and the pause propagates out to the person who can answer.

1,938 flights of seeded data. 158 tests, 88 offline. MIT.

https://github.com/fnusatvik07/a2a-multi-agent-travel
