---
format: 1920x1080
duration: 158s
message: "Five specialist agents, built on five frameworks that cannot share a process, book one trip by agreeing on how to talk."
arc: The ask → The four decisions → The team → The catch → The protocols → The request → The answers → The refusal → The re-ask → The money stops → The pause spreads → The close
audience: "Engineers building multi-agent systems, and the people deciding whether A2A is worth adopting."
mode: collaborative
music: none
---

## Video direction

**The cast, and how they are drawn.** Every agent has a character, and the
character is an icon, not a label. Each is a 2px ink stroke on a 64x64 grid,
drawn in the same hand, and each **draws itself on** with a stroke sweep the
first time you meet it.

| Agent | Icon | Framework mark |
|---|---|---|
| Concierge | a desk bell: dome, base, and the button on top | `assets/logos/langchain.svg` |
| Skyline | a wing, swept, three feather lines | `assets/logos/google.svg` |
| Hearth | a pitched roof over a bed | `assets/logos/crewai.svg` |
| Sentinel | a shield with one rule line across it | `assets/logos/llamaindex.png` |
| Ledger | a balance, beam and two pans | `assets/logos/pydantic.svg` |

The framework marks are real brand SVGs, rendered in a single ink at ~28px
under the agent's name. They are set in one colour on purpose: five brand
palettes on one screen is logo soup, and the point is that these are five
different stacks, not five different brands competing for attention.

**No ports, no URLs, no hostnames anywhere in the film.** `:8001` told the
viewer nothing. The identity of an agent is its icon and its name.

**Messages are objects.** When one agent gives another work, a small ink
envelope leaves the sender, travels the wire on a shallow arc, and lands on the
receiver, carrying one or two words. Work going out reads solid; an answer
coming back reads hollow. A refusal turns coral and comes back the way it came.
Nothing is ever implied by a static arrow.

**Palette, from `frame.md`.** Warm cream ground. Ink for everything that works.
Navy only where the frame shows literal machine text. **Coral is rationed to
three moments in the whole film:** the failure to install, Sentinel's refusal,
and Ledger's halt. Nowhere else, so that when it appears you know something has
gone wrong.

**Motion grammar.** Long-tail settles (`power3`), smooth over bouncy, one
overshoot in the entire film (the close). Reveals are cued to the spoken word
that names them, and the back half of every shot carries reveals too. Icons
draw on; they never fade in.

**Rhythm.** Frames 5, 9 and 12 are held reads that stop dead. They sit either
side of the two busiest shots, 8 and 11, so the film breathes.

**Negative list.** No bokeh, no purple-blue "AI" gradients, no glow behind
everything, no browser chrome, no fake cursors, no five-colour agent rainbow,
no port numbers, no stock iconography that was not drawn for this film. Neither
motion failure mode: nothing front-loads and freezes, nothing drifts like a
screensaver.

**Caption band.** Bottom ~17% is the caption pill. All content caps at y=896; a
centred hero anchors at y ≈ 454.

## Frame 1 — The ask

- scene: One trip, one city, one date. The business situation before any technology
- duration: 8.45s
- transition_in: cut
- status: animated
- src: compositions/frames/01-the-ask.html
- poster: 6.4s
- blueprint: kinetic-type-beats (Adapt)
- focal: the phrase "one engineer in Tokyo"
- roles: the sentence = foreground subject · a single ink map marker = supporting · hairline grid = background (dim ~15%)
- voiceover: "A robotics company needs one engineer in Tokyo next month, for a customer review. Simple ask. Four separate decisions."

Adapt: keep the beat structure, but the beats are a plain business sentence
rather than a claim. No product name, no architecture, no agents yet. The film
earns those.

Scene 1 (0.0-4.2s): cream ground, hairline grid at ~15%. The sentence assembles per word, centred, display ramp: "A robotics company needs one engineer in Tokyo next month." A small ink map marker draws itself beside "Tokyo" on that word (SVG self-draw). Centered, ~55% of frame.
Scene 2 (4.2-6.0s): the sentence drops to ~40% ink and lifts to the upper third. "Simple ask." lands beneath it, larger (kinetic beat-slam).
Scene 3 (6.0-8.45s): hard-cut swap in place: "Four separate decisions." replaces it on the beat. Four faint ink tick marks appear in a row beneath, empty, waiting to be filled by the next frame. Settle STILL.

## Frame 2 — The four decisions

- scene: Four icons fill the four ticks, one per spoken decision
- duration: 7.05s
- transition_in: cut
- status: animated
- src: compositions/frames/02-four-decisions.html
- poster: 5.6s
- blueprint: grid-card-assemble (Adapt)
- focal: the row of four icons
- roles: four icons with one-word captions = foreground subject · the row rule = supporting · cream ground = background
- voiceover: "What she flies. Where she sleeps. Whether the policy allows it. And who signs for it."

Adapt: the cascade is not staggered; each item lands on its own spoken beat.
This frame teaches the icon language the rest of the film depends on, so the
drawing is slow enough to read.

Scene 1 (0.0-1.9s): the four ticks from Frame 1 become four slots on a full-width strip. On "flies", slot one fills: a swept wing draws itself in 2px ink, caption "flies" in mono beneath (SVG self-draw).
Scene 2 (1.9-3.4s): on "sleeps", slot two draws a pitched roof over a bed, caption "sleeps".
Scene 3 (3.4-5.2s): on "policy", slot three draws a shield with one rule line, caption "policy".
Scene 4 (5.2-7.05s): on "signs", slot four draws a balance, caption "signs". All four now read as a set, evenly spaced, and hold STILL. These are the same four glyphs that will become agents in the next frame.

## Frame 3 — The team

- scene: The four icons become named agents, and a fifth arrives to run the desk
- duration: 16.25s
- transition_in: crossfade
- status: animated
- src: compositions/frames/03-the-team.html
- poster: 13.0s
- blueprint: constellation-hub (Adapt)
- focal: the five agent cards
- roles: five agent cards, each icon + name = foreground subject · the desk rule connecting them = supporting · hairline grid = background (dim ~15%)
- voiceover: "So there are five of them. Skyline books the air. Hearth finds the room. Sentinel knows the rulebook. Ledger holds the money. And the Concierge takes the request and runs the desk."

Adapt: keep the signature of nodes arriving and resolving on a centre, but the
arrangement is a working desk, not a ring: four specialists in a row, the
Concierge arriving last and above them. The four icons are already on screen
from Frame 2, so they are promoted rather than introduced.

Scene 1 (0.0-2.2s): the four icons from Frame 2 slide from their strip into four card positions, keeping their glyphs. Cards are hairline, cream, unlabelled.
Scene 2 (2.2-9.6s): each card takes its name on its spoken cue and not before: "Skyline" with "books the air" beneath, then "Hearth" / "finds the room", then "Sentinel" / "knows the rulebook", then "Ledger" / "holds the money". As each name lands its icon brightens from ~50% to full ink.
Scene 3 (9.6-13.4s): on "the Concierge", a fifth card arrives ABOVE the row, larger, and a desk bell draws itself inside it (SVG self-draw). An ink rule extends from it down to each of the four, drawing left to right.
Scene 4 (13.4-16.25s): the assembly settles. A slow ~2% push-in runs underneath and stops. No framework marks yet; this frame is about jobs, not stacks.

## Frame 4 — The catch

- scene: The five frameworks arrive, and refuse to fit in one process
- duration: 18.4s
- transition_in: cut
- status: animated
- src: compositions/frames/04-the-catch.html
- poster: 15.5s
- blueprint: compose
- focal: the five brand marks failing to fit one container
- roles: five brand marks = foreground subject · the "one process" container = foreground subject · the dependency pins = supporting · cream ground = background
- voiceover: "Here is the catch. They were not built by the same team, and they do not run on the same stack. LangGraph. Google's ADK. CrewAI. LlamaIndex. Pydantic AI. Put all five in one Python process and it will not even install."

Compose: no blueprint carries "five things that will not fit", so this is built
from the vocabulary. The signature move is the container failing.

Scene 1 (0.0-3.4s): the five agent cards from Frame 3 hold, dimmed to ~55%. "Here is the catch." sets in the display ramp, upper left, then clears.
Scene 2 (3.4-10.4s): on each framework name in turn, its real brand mark drops onto the matching agent card, in single ink at ~28px beneath the name: LangChain onto Concierge, Google onto Skyline, CrewAI onto Hearth, the LlamaIndex llama onto Sentinel, Pydantic onto Ledger. Each mark arrives with a short spring settle, no overshoot.
Scene 3 (10.4-14.6s): the five marks detach from their cards and converge toward the centre, where a hairline container has drawn itself labelled "one Python process" in mono. Four fit. The fifth cannot: it presses against the boundary, the container edge flares coral, and the mark is pushed back out (cluster→outward expansion, reversed and blocked).
Scene 4 (14.6-18.4s): beneath the failed container two navy code plates type the real reason, one line each: "crewai 1.15.17   requires openai>=2.30,<3" and "pydantic-ai 2.35.1   requires openai>=3". A coral rule joins them. The word "install" lands last and holds STILL. This is the first of the film's three coral moments.

## Frame 5 — Two protocols

- scene: Two layers appear under the team: one to tools, one between agents
- duration: 16.15s
- transition_in: crossfade
- status: animated
- src: compositions/frames/05-two-protocols.html
- poster: 13.4s
- blueprint: kinetic-type-beats (Adapt)
- focal: the two protocol layers
- roles: the MCP layer beneath the agents = foreground subject · the A2A wires between agents = foreground subject · the task token = supporting hero · agent row (dim ~45%) = background
- voiceover: "So they do not share a process. They share two protocols. MCP is how an agent reaches its tools. A2A is how one agent hands work to another. Not a function call. A task, with a life of its own."

Adapt: the beats are structural rather than typographic. Each protocol is
introduced by drawing where it actually sits, so the geometry teaches the
distinction before the words finish. Held frame: it resolves and stops.

Scene 1 (0.0-3.6s): the failed container from Frame 4 clears. The five agents return, dimmed to ~45%, in their Frame 3 positions. "They share two protocols." sets small at the top.
Scene 2 (3.6-8.0s): on "MCP", a wide plate draws itself BENEATH the four specialists, labelled "MCP" in mono with "an agent reaches its tools" beside it. Four short vertical wires draw down from the specialists into it, all four at once. The plate reads as shared ground, not a sixth agent.
Scene 3 (8.0-12.0s): on "A2A", horizontal wires draw BETWEEN the agents and up to the Concierge, in a different weight from the vertical ones. Label "A2A" with "one agent hands work to another".
Scene 4 (12.0-16.15s): on "Not a function call", a small solid dot travels one A2A wire and vanishes instantly, dismissed. On "A task, with a life of its own", a rounded ink token arrives instead and STAYS, and a thin ring draws around it in three ticks (submitted, working, waiting). Everything else stops. Only the ring completes, then holds.

## Frame 6 — The request

- scene: The ask arrives in plain English and two agents are commissioned at once
- duration: 8.9s
- transition_in: cut
- status: animated
- src: compositions/frames/06-the-request.html
- poster: 7.4s
- blueprint: typewriter-reveal (Adapt)
- focal: the typed request, then the two envelopes leaving
- roles: the request plate = foreground subject · two travelling envelopes = foreground subject · the agent row (dim ~35%) = background
- voiceover: "The request arrives in plain English. The Concierge reads it, and puts two agents to work at the same time."

Adapt: the typewriter is only the first half; the second half is the first
message flight in the film, so the audience learns what an envelope means here.

Scene 1 (0.0-4.6s): the agents recede to ~35% and sit as the ground. A hairline plate seats in the upper third and types, caret leading: "Get Mira to Tokyo, 14 to 17 October, near the customer's office." (type-on with caret).
Scene 2 (4.6-6.2s): the caret stops. The plate's border goes ink-strong for one beat. The Concierge's bell brightens to full ink.
Scene 3 (6.2-8.9s): two solid ink envelopes leave the Concierge at the same moment, travel their wires on shallow arcs, and land on Skyline and Hearth. Each carries one word: "flights" and "a room". Both receiving icons brighten as the envelope lands. Hold.

## Frame 7 — What came back

- scene: Two answers return, carrying real numbers
- duration: 13.75s
- transition_in: cut
- status: animated
- src: compositions/frames/07-what-came-back.html
- poster: 11.4s
- blueprint: agent-progress-theater (Adapt)
- focal: the two returned payloads
- roles: two result cards = foreground subject · two hollow return envelopes = supporting · the agent row = background
- voiceover: "Skyline comes back with United, premium economy, three thousand one hundred and ten dollars. Hearth comes back with a hotel two hundred metres from the customer's door, at two hundred and ninety-eight a night."

Adapt: the receipt cascade runs twice, from two agents, finishing at different
times because they do. Return envelopes are HOLLOW, which is the film's rule for
an answer.

Scene 1 (0.0-6.4s): a hollow envelope leaves Skyline, arcs back to the Concierge, and opens into a card: "United" then "premium economy" then the value "$3,110.48" landing large in the number ramp on its spoken syllable (value-scaled counter).
Scene 2 (6.4-12.2s): a hollow envelope leaves Hearth the same way and opens: the hotel name, then "200 m from the customer's door", then "$298.33 / night" landing large.
Scene 3 (12.2-13.75s): the Skyline card dims to ~50%. The hotel's nightly rate is left alone and bright. It is the last thing on screen, and the setup for the refusal.

## Frame 8 — Sentinel says no

- scene: The rulebook refuses the room, and the Concierge asks again instead of deciding
- duration: 19.9s
- transition_in: cut
- status: animated
- src: compositions/frames/08-sentinel-says-no.html
- poster: 16.6s
- blueprint: agent-progress-theater (Adapt)
- focal: the coral refusal travelling back, then the re-ask routing past the card
- roles: the hotel card = foreground subject · Sentinel's shield and its stamp = foreground subject · the re-ask envelope = foreground subject · dimmed agents = background
- voiceover: "Sentinel reads that, and says no. Policy caps Tokyo at two hundred and eighty. Now watch what the Concierge does not do. It does not overrule Sentinel. It does not overrule Hearth. It asks Hearth again, with the cap as a hard limit."

Adapt: the state mutation is a ruling arriving from a different agent. Three
moves must be separable in space and time: a refusal, a reason, and a re-ask
that visibly touches neither party's decision.

Scene 1 (0.0-4.0s): a solid envelope carries the hotel card from the Concierge to Sentinel. Sentinel's shield brightens, then a coral cross-rule strikes across it. The envelope returns HOLLOW and CORAL, and lands back on the Concierge. Second coral moment.
Scene 2 (4.0-8.4s): the returned envelope opens: a measurement line draws between "$298.33" and "cap $280.00", with "+$18.33" in coral beneath (SVG self-draw). Sentinel's own words set small: "policy caps Tokyo at two hundred and eighty".
Scene 3 (8.4-13.6s): on "what the Concierge does not do", two ghosted arrows appear briefly, one pointing at Sentinel and one at Hearth, and both are struck through and dismissed. The hotel card does not change. Nothing is chosen here, and the frame must show that nothing was.
Scene 4 (13.6-19.9s): a fresh solid envelope leaves the Concierge, routes visibly AROUND the hotel card without touching it, and lands on Hearth carrying "under $280". The coral drains out of the frame as it goes. Hold on Hearth's icon, lit and working.

## Frame 9 — The second answer

- scene: A compliant room comes back and the rulebook clears it
- duration: 5.7s
- transition_in: cut
- status: animated
- src: compositions/frames/09-second-answer.html
- poster: 4.6s
- blueprint: agent-progress-theater (Adapt)
- focal: the replacement card clearing
- roles: the new hotel card = foreground subject · Sentinel's shield with a clear mark = supporting · cream ground = background
- voiceover: "A hundred and eighty-nine a night, five hundred metres out. Sentinel clears it."

Adapt: short and clean, the exhale after the longest frame. Held read.

Scene 1 (0.0-3.0s): a hollow envelope returns from Hearth and opens in the same footprint the rejected card occupied: "$189.96 / night" and "500 m from the customer's door" (scale-swap).
Scene 2 (3.0-5.7s): the card travels to Sentinel, the shield's rule line completes rather than striking through, and a small ink "clear" sets beside it. No coral anywhere. Everything stops STILL.

## Frame 10 — Ledger stops

- scene: The total clears the budget, fails the threshold, and the balance locks
- duration: 18.05s
- transition_in: crossfade
- status: animated
- src: compositions/frames/10-ledger-stops.html
- poster: 15.0s
- blueprint: dataviz-countup (Adapt)
- focal: the total meeting the threshold
- roles: the total and the budget bar = foreground subject · Ledger's balance icon = foreground subject · threshold marker = supporting
- voiceover: "Then Ledger. Three thousand six hundred and eighty-eight dollars, against seven thousand six hundred left this quarter. It fits. But it is over the line where a human has to sign. So Ledger stops. Not fails. Stops, and waits."

Adapt: the count-up is measured against two things in sequence, and the second
one stops it. Ledger's balance icon is the instrument: it tips as the numbers
land, then locks. Held frame with a hard stop.

Scene 1 (0.0-4.2s): a solid envelope arrives at Ledger. Its balance icon enlarges to become the frame's instrument, beam level. A budget bar draws across beneath it, "$7,600.00 left this quarter" in mono at its right end.
Scene 2 (4.2-9.4s): "$3,688.76" counts up in the number ramp, the bar fills to just under half on the same ease, and the balance beam tips gently but settles level. An ink "fits" lands. For one beat this reads as a yes.
Scene 3 (9.4-14.0s): a second marker drops onto the bar much earlier along it: "the line where a human signs". The fill has already passed it. The balance beam tips hard the other way and LOCKS with a visible catch.
Scene 4 (14.0-18.05s): "fits" swaps for a coral "waiting". Third and final coral moment. Beneath it, in ink rather than machine text: "not failed. waiting." Everything stops dead for the last ~2s except a subtle jitter on the locked balance.

## Frame 11 — The pause spreads

- scene: The waiting travels agent to agent to a person, and the answer comes back
- duration: 15.2s
- transition_in: cut
- status: animated
- src: compositions/frames/11-pause-spreads.html
- poster: 11.0s
- blueprint: spatial-pan-stations (Adapt)
- focal: the identical waiting state on two agents, then a person
- roles: three stations on one wide canvas = foreground subject · the connecting rail = supporting · cream ground = background
- voiceover: "And the waiting spreads. The Concierge pauses too, and the question surfaces to the one person who can answer it. She approves. Both agents pick up exactly where they stopped. The trip is booked."

Adapt: the traversal carries a STATE rather than a narrative, and it makes a
return trip. Three stations: Ledger, Concierge, a person. Ledger and Concierge
must be given identical treatment, because the sameness is the whole argument.

Scene 1 (0.0-3.4s): pull back to reveal Ledger was station one on a wide canvas, its balance locked and its "waiting" chip lit. Three stations sit along a hairline rail; only the first is lit.
Scene 2 (3.4-7.0s): the camera pans right. The waiting chip travels the rail and lands on the Concierge, whose bell dims and takes an IDENTICAL chip. Frame the pan so both stations are readable at once.
Scene 3 (7.0-10.2s): the camera continues to station three, which is not an agent: no card, no icon, just a name and a question in the display ramp, "approve $3,688.76?".
Scene 4 (10.2-15.2s): an ink "approved" lands. The lit state sweeps back LEFT along the rail in one unbroken move, both chips clearing as it passes, the balance unlocking and levelling. It lands on Ledger, where a small ink "booked" sets. The camera returns with it. Settle.

## Frame 12 — The close

- scene: The claim the film opened with, now earned
- duration: 9.75s
- transition_in: crossfade
- status: animated
- src: compositions/frames/12-close.html
- poster: 7.6s
- blueprint: logo-assemble-lockup (Adapt)
- focal: the closing statement, then the repository
- roles: the five agents with their marks = background (dim ~16%) · the closing lines = foreground subject · the repo line = supporting
- voiceover: "Five specialists. Five frameworks. One conversation. Nobody is in charge of everybody. They just agreed on how to talk."

Adapt: what assembles is the film's own claim. The mark is a wordmark. Held
frame; the last two seconds do not move.

Scene 1 (0.0-3.6s): the rail recedes and the five agents return behind it at ~16%, complete and still, marks included, as texture rather than subject. "Five specialists. Five frameworks. One conversation." assembles in three beats, centred.
Scene 2 (3.6-6.4s): those lines drop to ~35% ink and "Nobody is in charge of everybody." lands beneath in the display ramp. A beat. Then "They just agreed on how to talk."
Scene 3 (6.4-9.75s): everything clears upward. "AtlasTrip" springs to centre with the coral spike ahead of it (the single overshoot in the film, small), and "github.com/fnusatvik07/a2a-multi-agent-travel" types beneath it in mono. Everything stops. No drift, no glow, no sting.
