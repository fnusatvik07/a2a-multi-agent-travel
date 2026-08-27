---
workflow: faceless-explainer
flow: automation
storyboard: yes
message: "Five AI agents on five incompatible frameworks cooperate over the A2A protocol, negotiate with each other, and stop for a human before spending money."
destination: youtube
aspect: "16:9"
language: en
audience: "Engineers building multi-agent systems, and the people deciding whether A2A is worth adopting."
length: 90
angle: concept
---

## Intent

An explainer for AtlasTrip, an open-source project at
github.com/fnusatvik07/a2a-multi-agent-travel.

The interesting claim is not "look, five agents". It is that the five agents
**cannot share a Python process** — CrewAI and Pydantic AI pin incompatible
`openai` versions, Google ADK and LlamaIndex pin incompatible `mcp` versions —
and that this is the ordinary state of the agent ecosystem, not a contrived
constraint. A2A is what lets them cooperate anyway.

The video should land three things, in order:

1. **The problem.** Agents from different teams, on different frameworks, in
   different processes. They cannot import each other.
2. **The shape of the answer.** MCP gives an agent its tools. A2A lets agents
   give each other work. One shared MCP server, five agents, one context id.
3. **What that buys you.** Two moments a single-process agent cannot produce:
   - Hearth picks a hotel $18 over the policy cap because it is 210 metres from
     the customer's door. Sentinel overrules it. The orchestrator does not
     decide for either of them; it goes back and asks again with the cap
     enforced.
   - Ledger will not spend $3,688 without a human. It pauses its task in
     `input-required`. The orchestrator pauses its own task too, so the
     question travels all the way out to the person who can answer it.

## Notes

- Real numbers from a real run. Do not round or invent: $3,110.48 flights,
  $298.33 a night rejected, $189.96 a night accepted, $3,688.76 total,
  $7,600.00 remaining in the quarter, AUTH code issued on approval.
- The five agents: Concierge (LangGraph), Skyline (Google ADK), Hearth
  (CrewAI), Sentinel (LlamaIndex), Ledger (Pydantic AI).
- Tone: an engineer explaining something they actually built. No hype, no
  "revolutionary", no "imagine a world where".

## Assets

- `docs/diagrams/architecture.png`, `trip-sequence.png`, `task-lifecycle.png`
  exist in the repo. They are reference for accuracy; the video's visuals are
  invented, not these PNGs pasted in.
