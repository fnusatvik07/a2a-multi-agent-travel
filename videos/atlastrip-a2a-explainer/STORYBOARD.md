---
format: 1920x1080
duration: 93s
message: "Five AI agents on five incompatible frameworks cooperate over the A2A protocol, negotiate with each other, and stop for a human before spending money."
arc: Hook → Constraint → Mechanism → Cast → The ask → Fan-out → Negotiation → The pause → Propagation → Close
audience: "Engineers building multi-agent systems, and the people deciding whether A2A is worth adopting."
mode: collaborative
music: none
---

## Video direction

**Palette (from `frame.md`, never invented).** Warm cream (`cream`) is the ground
of every frame. Ink is the voice. `tile` / `tile-strong` carry cards and rails.
The navy surface (`navy`, `navy-soft`, `navy-elev`) appears only where the frame
is showing something that is literally machine text: a dependency pin, a wire
payload, a task state. **Coral is scarce voltage and is rationed to four
moments in the whole film**: the word `cannot` in Frame 1, the collision in
Frame 2, the policy violation in Frame 7, and the halt in Frame 8. It appears
nowhere else, so that when it appears the eye knows something has gone wrong.
The five agents are *not* given five colours; they are distinguished by their
mono framework label and their position, which keeps the film editorial rather
than making it a rainbow.

**Motion grammar.** Long-tail settles throughout (`power3`); smooth over bouncy,
with no overshoot anywhere except the single spring in Frame 10's lockup. One
camera feel: pushes are slow and small, never more than a few percent. Every
reveal is cued to the spoken word that names it, and the back half of each shot
carries reveals as well as the front.

**Reveal model.** Nothing is on screen before the voiceover reaches it. An
enumeration arrives item by item on its own spoken cue. A number lands on the
syllable that says it. A diagram gains a layer, never appears whole.

**Rhythm and held frames.** Frames 3, 8 and 10 are held reads: the content
resolves and then stops, completely still, with at most a subtle jitter on the
hero. They sit either side of the two busiest shots (Frames 7 and 9) so the film
breathes. Everything else reveals continuously against its line.

**Negative list.** No bokeh, no purple-blue "AI" gradients, no glow behind
everything, no browser chrome, no fake cursors, no floating decorative shapes
standing in for a designed idea, no five-colour agent rainbow, no logo soup. And
neither motion failure mode: nothing front-loads and then freezes, nothing
drifts independently like a screensaver.

**Caption band.** Captions occupy the bottom ~17%. All primary content caps at
the band top; a centred hero anchors at y ≈ 454, not 540. Background fields and
hairline grids are exempt and stay full-bleed.

## Frame 1 — Five agents, no shared runtime

- scene: Three statements land one after another, the third one turning the first two into a problem
- duration: 4.693s
- transition_in: cut
- status: animated
- src: compositions/frames/01-no-shared-runtime.html
- poster: 3.6s
- blueprint: kinetic-type-beats (Reproduce)
- focal: the word `cannot`
- roles: the three statements = foreground subject · hairline ink grid = background (dim ~18%) · nothing else
- voiceover: "Five AI agents. Five different frameworks. And they cannot import each other."

Cold open on the claim, not on a logo. The first two lines sound like a
feature; the third turns them into a constraint, which is the actual subject of
the video. No architecture yet, no product name yet.

Reproduce: three beats, each its own move, resolving on the third. The signature
move is the beat-slam; the third beat is where it turns.

Scene 1 (0.0-1.4s): cream ground with a 1px ink hairline grid at ~18%. `Five AI agents.` slams in centred, display ramp, near full-bleed (kinetic beat-slam). Nothing else exists. Centered, ~55% of frame, 3 depth layers (grid, type, a faint tile wash behind the type).
Scene 2 (1.4-2.9s): hard-cut word-swap in place: `Five different frameworks.` replaces it on the beat, same optical centre, same size (hard-cut / flash word-swap). The grid holds still.
Scene 3 (2.9-4.7s): the third line assembles per-word underneath the second, which drops to ~40% ink: `And they cannot import each other.` The word `cannot` alone lands in coral and takes a hand-drawn circle sweep on its spoken syllable (per-word staggered reveal + highlight / circle). Frame settles STILL on the circled word. Asymmetric stack, hero at y ≈ 420.


## Frame 2 — The constraint is real

- scene: Two dependency pins collide on a code surface; the resolver's refusal is the punchline
- duration: 9.408s
- transition_in: cut
- status: animated
- src: compositions/frames/02-the-constraint.html
- poster: 7.0s
- blueprint: kinetic-type-beats (Adapt)
- focal: the two colliding version pins
- roles: two navy code plates = foreground subject · the resolver's refusal line = supporting · cream ground with a hairline centre rule = background
- voiceover: "That's not a design choice. CrewAI pins one version of the OpenAI client. Pydantic AI pins another. A shared environment cannot exist."

The load-bearing beat. Anyone can claim their agents are independent; this
shows they have no choice. Real version strings from the real lockfiles, on the
navy code surface. The two pins should read as irreconcilable before the
narration says so.

Adapt: keep the beat structure and the in-place emphasis, but the beats are two
real dependency pins arriving on a code surface instead of bare type. The
signature slam lands on the collision, not on a word.

Scene 1 (0.0-2.2s): the previous line clears. `That's not a design choice.` sets small and left, mono-label ramp, upper third. A single navy plate slides up from below centre, empty. Split-screen prepared but only the left half is populated. 3 depth layers.
Scene 2 (2.2-4.6s): on `CrewAI pins one version`, the left plate types its line in mono on navy: `crewai 1.15.17   requires openai>=2.30,<3` (type-on with caret). The caret blinks once and stops.
Scene 3 (4.6-6.8s): on `Pydantic AI pins another`, the right plate arrives from the right edge and types: `pydantic-ai 2.35.1   requires openai>=3` (type-on with caret). Both plates now sit side by side, split-screen 50/50, a hairline ink rule between them.
Scene 4 (6.8-9.4s): the two version constraints pull toward each other and stop hard against the centre rule; the rule flares coral and a small coral `✕` seats on it (spring-pop entrance, no overshoot). Beneath, in ink: `no shared environment exists`. Everything holds STILL. The coral is the only saturated thing on screen.


## Frame 3 — Two protocols, two jobs

- scene: One line splits into two, each protocol taking a side and holding it
- duration: 10.283s
- transition_in: crossfade
- status: animated
- src: compositions/frames/03-two-protocols.html
- poster: 7.4s
- blueprint: kinetic-type-beats (Adapt)
- focal: the two-band definition
- roles: two stacked full-width bands = foreground subject · the word `task` = supporting hero · cream ground = background
- voiceover: "So the agents share a protocol instead. MCP gives an agent its tools. A2A lets agents give each other work. Not a function call. A task, with a lifecycle."

The one distinction the whole video rests on. It has to be legible in four
seconds and survive being quoted out of context, because it is the sentence
people will repeat.

Adapt: keep the build-across-beats structure; the shape becomes two stacked
full-width bands rather than centred slams, so the two protocols are visibly
peers rather than a comparison with a winner. Held frame: it resolves and stops.

Scene 1 (0.0-2.4s): everything from Frame 2 clears upward. `So the agents share a protocol instead.` sets centred in the display ramp, then shrinks and parks as a kicker at the top (scale-swap). Full-width strip layout, two empty bands ruled by hairlines below it.
Scene 2 (2.4-4.8s): the upper band fills on its spoken cue: `MCP` in mono-label at the left gutter, then `gives an agent its tools` assembling per-word across the band (per-word staggered reveal).
Scene 3 (4.8-7.2s): the lower band fills the same way on its cue: `A2A` at the left gutter, `lets agents give each other work`. Both bands now read as a matched pair, equal weight, equal ink.
Scene 4 (7.2-10.3s): under the lower band a short line arrives in two beats: `Not a function call.` then, after a clear gap, `A task. With a lifecycle.` The word `task` scales up ~1.6x and holds. Frame goes completely STILL for the last two seconds; only a subtle jitter on `task` keeps it alive.


## Frame 4 — The cast

- scene: Five named services assemble around one shared tool server
- duration: 14.976s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-the-cast.html
- poster: 11.5s
- blueprint: constellation-hub (Adapt)
- focal: the five service cards and the server beneath them
- roles: five hairline cards = foreground subject · the MCP server plate = foreground subject (shared ground) · SVG connectors = supporting · hairline grid = background (dim ~15%)
- voiceover: "Five services, five ports, five frameworks. A concierge on LangGraph. Flights on Google ADK. Lodging on CrewAI. Policy on LlamaIndex. Money on Pydantic AI. All four specialists read one MCP server."

The architecture, arriving in the order the narration names it, so the diagram
is being built rather than displayed. The MCP server has to read as shared
ground underneath the four specialists, not as a sixth peer.

Adapt: keep the signature — nodes springing into place around a centre and
resolving on the core — but the arrangement is architectural, not a ring: one
orchestrator above, four specialists in a row, one shared server beneath them.
The reveal order is exactly the order the voiceover names them, so the diagram
is being built rather than displayed.

Scene 1 (0.0-2.6s): cream ground, hairline grid at ~15%. On `Five services, five ports, five frameworks`, five empty hairline card outlines pop into their final positions in one staggered cascade, still unlabelled (spring-pop entrance, staggered). Layered depth, 3 layers.
Scene 2 (2.6-5.0s): on `A concierge on LangGraph`, the top card fills: `Concierge` in the display ramp, `LANGGRAPH` beneath it in mono-label, `:8000` in the corner. An SVG connector draws downward from it toward the row below (SVG self-draw).
Scene 3 (5.0-10.2s): the four specialist cards fill left to right, each exactly on its spoken cue and not before: `Skyline / GOOGLE ADK / :8001`, `Hearth / CREWAI / :8002`, `Sentinel / LLAMAINDEX / :8003`, `Ledger / PYDANTIC AI / :8004`. As each fills, its connector draws up to the Concierge. Asymmetric depth: the filled cards sit forward, the unfilled ones sit back at ~45% opacity.
Scene 4 (10.2-15.0s): on `All four specialists read one MCP server`, a wide plate slides up beneath the row, labelled `TRAVEL INVENTORY MCP` and `:8100`, and four connectors draw down into it at once. The whole assembly then settles; a slow ~2% push-in runs underneath for the last beat and stops (push / focus / drift).


## Frame 5 — One sentence

- scene: A request types itself into an empty field and is sent
- duration: 6.763s
- transition_in: cut
- status: animated
- src: compositions/frames/05-one-sentence.html
- poster: 5.2s
- blueprint: typewriter-reveal (Reproduce)
- focal: the typed request
- roles: the input field = foreground subject · the settled network from Frame 4 = background (dim ~25%, blurred)
- voiceover: "Someone types one sentence. Mira needs to be in Tokyo for the customer review, the fourteenth to the seventeenth."

The pivot from architecture to a real run. Everything after this is one trace
through the network, with real numbers.

Reproduce: a human types a line as a human would, and it is sent. The signature
is the live caret.

Scene 1 (0.0-1.2s): the Frame 4 assembly recedes and blurs to ~25% (depth-of-field / selective-blur), becoming the background. A single hairline input plate seats across the upper-middle, empty, caret blinking. Asymmetric 70/30, the plate taking the 70.
Scene 2 (1.2-5.4s): the request types itself in the body ramp, caret leading: `Mira Halvorsen needs to be in Tokyo for the Kaisei customer review, 14 to 17 October.` (type-on with caret). Real typing rhythm, faster on common words, a small pause at the comma.
Scene 3 (5.4-6.8s): the caret stops. The plate's border goes ink-strong for one beat and the line settles; a small mono tag `sent` appears at its right edge. The blurred network behind it brightens very slightly, as if waking. Hold.


## Frame 6 — Two agents at once

- scene: Two work lanes run in parallel and return their results
- duration: 8.512s
- transition_in: cut
- status: animated
- src: compositions/frames/06-two-agents-at-once.html
- poster: 6.4s
- blueprint: agent-progress-theater (Adapt)
- focal: the two working lanes and the two results
- roles: two vertical lanes = foreground subject · the result values = supporting hero · cream ground with a hairline centre rule = background
- voiceover: "The concierge commissions two agents at once. Flights, three thousand one hundred and ten dollars. A hotel at two hundred and ninety-eight a night."

Parallelism shown as two lanes finishing at different times, because they do.
The hotel price is planted here and paid off in the next frame, so it should be
the last thing on screen.

Adapt: keep the working-state theater and the receipt cascade, but run TWO
lanes at once and let them finish at different times, because they do. No
trigger click; the trigger already happened in Frame 5.

Scene 1 (0.0-2.0s): split-screen 50/50, hairline rule down the centre. Two lanes label themselves in mono at the top: `SKYLINE` left, `HEARTH` right. Under each, a thin progress rail begins to fill and a status phrase swaps in place (`searching fares` / `searching lodging`) (in-place token cycle).
Scene 2 (2.0-4.8s): the left rail completes first. Its receipt cascades in: `UA 837 / UA 838` in mono, `premium economy`, then the value `$3,110.48` landing large in the number ramp on its spoken syllable (value-scaled counter). The right lane is still visibly working.
Scene 3 (4.8-8.5s): the right rail completes. Its receipt cascades: `Shinagawa Bay Tower`, `0.21 km from the venue`, then `$298.33 / night` landing large. That number is the last thing to arrive and it is left holding, alone and bright, as the left lane dims to ~50%. Hold on it; it is the setup for Frame 7.


## Frame 7 — The negotiation

- scene: The hotel price meets the policy cap, is overruled, and the request goes back out
- duration: 12.544s
- transition_in: cut
- status: animated
- src: compositions/frames/07-the-negotiation.html
- poster: 9.6s
- blueprint: agent-progress-theater (Adapt)
- focal: the policy finding overruling the price
- roles: the hotel card = foreground subject · the policy rail = foreground subject · the re-ask = supporting · dimmed lanes from Frame 6 = background
- voiceover: "That room is eighteen dollars over policy. Hearth took it anyway, because it's two hundred metres from the customer's door. Sentinel overrules it. The concierge doesn't pick a side; it asks again, with the cap enforced."

The centrepiece, and the longest frame. Three moves have to be separable: a
judgement, an overrule, and a re-ask. The concierge deciding *nothing* is the
point, so the frame must not show it choosing a hotel.

Adapt: keep the receipt cascade and the state mutation, but the mutation here is
a *ruling arriving from a different agent*, and the frame must show three
separable moves: a judgement, an overrule, and a re-ask. The Concierge must
never be shown choosing a hotel, because it does not.

Scene 1 (0.0-3.0s): asymmetric 70/30. The hotel card carries over from Frame 6 into the left 70. On the spoken cue a measurement line draws between `$298.33` and a small mono marker `cap $280.00` (SVG self-draw), and the difference `+$18.33` sets in coral beneath it. Hearth's own justification types beneath the card in a lighter ink: `210 m from the customer's door`.
Scene 2 (3.0-6.4s): on `Sentinel overrules it`, a narrow navy rail slides in from the right 30 and stamps its finding: `TRV-003  LODGING NIGHTLY CAP` in mono, then `VIOLATION` in coral. The hotel card's border goes coral and the card drops back in depth ~8%. This is the only coral in the frame besides the difference.
Scene 3 (6.4-9.6s): on `The concierge doesn't pick a side`, an ink connector draws from the Concierge label at top, PAST the hotel card without touching it, and back out to the Hearth lane. A single mono line rides it: `source_stay  enforce_cap = true` (SVG self-draw). Nothing about the card changes; the point is that nothing was chosen here.
Scene 4 (9.6-12.5s): the old card scale-swaps out and the replacement arrives in its place: `Konan Garden Hotel`, `0.56 km`, `$189.96 / night` (scale-swap). The coral drains out of the frame entirely as the finding rail stamps `CLEARED` in ink. Settle STILL.


## Frame 8 — The money stops

- scene: A total meets a budget, clears it, then meets a threshold and halts
- duration: 7.637s
- transition_in: crossfade
- status: animated
- src: compositions/frames/08-the-money-stops.html
- poster: 5.8s
- blueprint: dataviz-countup (Adapt)
- focal: the trip total meeting the threshold
- roles: the total = foreground subject · the budget bar and the threshold marker = supporting · cream ground = background
- voiceover: "Then the money. Three thousand six hundred and eighty-eight dollars. It fits the budget, but it's over the approval threshold. So Ledger stops."

Two comparisons in sequence, and the second one is the one that bites. The halt
should feel like a held breath, not an error.

Adapt: keep the count-up hero, but it is measured against TWO things in
sequence, and the second one stops it. The shot ends held, not resolved. This is
a held frame: after the halt, everything is completely still.

Scene 1 (0.0-2.4s): the frame clears to cream. A single horizontal budget bar draws across the middle with `$7,600.00 remaining this quarter` in mono at its right end (bars / progress / star wipe). Centered, hero at y ≈ 454.
Scene 2 (2.4-4.4s): `$3,688.76` counts up from zero in the number ramp above the bar, and a fill sweeps the bar to just under half as the number lands (value-scaled counter). A small ink tick reads `fits`. For one beat this looks like a yes.
Scene 3 (4.4-7.6s): a second marker drops onto the bar much earlier along it, labelled `auto-approval threshold  $3,000.00`. The total's fill has already passed it. The tick flips from `fits` to a coral `HELD`, the bar's fill freezes visibly mid-sweep, and a mono line stamps beneath: `TASK_STATE_INPUT_REQUIRED`. Everything stops dead. No motion at all for the final ~1.5s except a subtle jitter on the stamped state.


## Frame 9 — The pause travels

- scene: The paused state moves outward from one agent to the person, and the answer comes back
- duration: 8.469s
- transition_in: cut
- status: animated
- src: compositions/frames/09-the-pause-travels.html
- poster: 6.0s
- blueprint: spatial-pan-stations (Adapt)
- focal: the pause moving along the chain
- roles: three stations on one wide canvas = foreground subject · the connecting rail = supporting · cream ground = background
- voiceover: "Not fails. Stops, and waits. And that pause travels outward, through the orchestrator, to the person who can answer it. They approve. Both tasks resume."

The protocol's best moment. The distinction between failed and waiting carries
it, and the propagation has to be visibly a chain rather than a callback.

Adapt: keep the signature — pre-placed stations on an oversized canvas
traversed by one camera — but the traversal carries a STATE rather than a
narrative, and it makes a return trip. Three stations: Ledger, Concierge,
a person.

Scene 1 (0.0-2.0s): pull back from Frame 8's stamp to reveal it was station one on a wide canvas. `Not fails.` sets, holds, clears. `Stops, and waits.` replaces it (hard-cut word-swap). Full-width strip, three stations along a hairline rail, only the first lit.
Scene 2 (2.0-4.6s): the camera pans right along the rail (pan / focus-lock). Station two lights as it arrives: `CONCIERGE`, and its own state stamps to match: `INPUT_REQUIRED`. The identical stamp on two different agents is the whole idea; give them identical treatment.
Scene 3 (4.6-6.4s): the camera continues to station three, which is not an agent: a plain ink line reading `elena.marchetti@ ` and a single question, `approve $3,688.76?`. It sits alone, unstamped, waiting.
Scene 4 (6.4-8.5s): on `They approve`, an ink `approved` lands at station three, and the lit state travels back LEFT along the rail in one unbroken sweep, both stamps flipping to `COMPLETED` as it passes (cut-the-curve, matched velocity). The camera returns with it and lands on station one, where `AUTH-351693FF2A` stamps in mono. Settle.


## Frame 10 — Close

- scene: The thesis restated over the settled network, then the repository
- duration: 6.123s
- transition_in: crossfade
- status: animated
- src: compositions/frames/10-close.html
- poster: 4.6s
- blueprint: logo-assemble-lockup (Adapt)
- focal: the wordmark and the repository line
- roles: the settled five-agent assembly = background (dim ~30%) · the closing statement = foreground subject · the repo URL = supporting
- voiceover: "Nothing here is one process pretending to be a team. It's five, on a protocol. The code is on GitHub."

Land the claim the video opened with, now earned, and hand over the URL. No
call to action beyond the repository.

Adapt: keep the assemble-and-settle finish, but what assembles is the film's
own claim, and the mark is a wordmark rather than a logo. Held frame; the last
two seconds do not move.

Scene 1 (0.0-2.2s): the station rail recedes and the Frame 4 assembly returns behind it at ~30%, complete and still, as the ground. `Nothing here is one process pretending to be a team.` assembles per-word centred over it (per-word staggered reveal).
Scene 2 (2.2-4.0s): that line drops to ~40% ink and `It's five, on a protocol.` lands beneath it in the display ramp, larger, on its spoken beat. The five cards behind it each flash their hairline border once, in sequence, and go quiet.
Scene 3 (4.0-6.1s): both lines clear upward. `AtlasTrip` springs to centre in the display ramp with the coral ✱ spike ahead of it (spring-pop entrance, the single overshoot in the film), and `github.com/fnusatvik07/a2a-multi-agent-travel` types beneath it in mono (type-on with caret). Everything stops. No drift, no glow, no outro sting.

