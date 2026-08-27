#!/usr/bin/env python
"""Generate the draw.io diagrams.

The diagrams are produced from code rather than drawn by hand so that the
geometry is exact, the palette is consistent across all three, and a change to
the architecture can be reflected by editing one file instead of nudging boxes.

Output: docs/diagrams/atlastrip.drawio, a three page file.

    1  Architecture     what talks to what
    2  Trip sequence    what happens, in order, including the renegotiation
    3  Task lifecycle   the A2A states an agent moves a task through

Open it at https://app.diagrams.net or in the draw.io desktop app.
"""

from __future__ import annotations

import html
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams"

# --------------------------------------------------------------------------
# Palette. One hue per role, kept muted so the labels stay the loudest thing
# on the page.
# --------------------------------------------------------------------------

INK = "#1A202C"
MUTED = "#5A6675"
HAIRLINE = "#CBD5E0"

ROLES = {
    "client": ("#FFFFFF", "#A0AEC0", INK),
    "orchestrator": ("#EEF0FF", "#4C51BF", "#2A2F86"),
    "air": ("#E8F1FE", "#2B6CB0", "#1A4E85"),
    "stay": ("#FDF2E3", "#B7791F", "#8A5A12"),
    "policy": ("#E9F6EC", "#2F855A", "#1F5F40"),
    "money": ("#FDECF2", "#B83280", "#8B2160"),
    "tools": ("#E4F5F5", "#2C7A7B", "#1D5859"),
    "data": ("#EDF2F7", "#4A5568", "#2D3748"),
    "note": ("#FFFFFF", "#E2E8F0", MUTED),
}

FONT = "Helvetica"


def fill(role: str) -> str:
    background, stroke, text = ROLES[role]
    return f"fillColor={background};strokeColor={stroke};fontColor={text}"


class Page:
    """One diagram page. Collects cells and renders the mxGraphModel."""

    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height
        self.cells: list[str] = []
        self._next = 0

    def _id(self) -> str:
        self._next += 1
        return f"n{self._next}"

    def node(self, label: str, x: int, y: int, w: int, h: int, style: str) -> str:
        node_id = self._id()
        self.cells.append(
            f'<mxCell id="{node_id}" value="{escape(label)}" style="{escape(style)}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f"</mxCell>"
        )
        return node_id

    def edge(self, source: str, target: str, label: str = "", style: str = "") -> str:
        edge_id = self._id()
        self.cells.append(
            f'<mxCell id="{edge_id}" value="{escape(label)}" style="{escape(style)}" '
            f'edge="1" parent="1" source="{source}" target="{target}">'
            f'<mxGeometry relative="1" as="geometry"/>'
            f"</mxCell>"
        )
        return edge_id

    def render(self) -> str:
        return (
            f'<diagram name="{escape(self.name)}">'
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="0" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            f'pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
            f'math="0" shadow="0">'
            f"<root>"
            f'<mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(self.cells)
            + "</root></mxGraphModel></diagram>"
        )


# --------------------------------------------------------------------------
# Shared styles
# --------------------------------------------------------------------------


def box(role: str, radius: int = 8, bold_first_line: bool = True) -> str:
    return (
        f"rounded=1;arcSize={radius};whiteSpace=wrap;html=1;{fill(role)};"
        f"fontFamily={FONT};fontSize=12;align=center;verticalAlign=middle;"
        f"strokeWidth=1.5;spacing=6"
        + (";fontStyle=0" if not bold_first_line else "")
    )


def title_style(size: int = 22) -> str:
    return (
        f"text;html=1;align=left;verticalAlign=middle;fontFamily={FONT};"
        f"fontSize={size};fontStyle=1;fontColor={INK};strokeColor=none;fillColor=none"
    )


def caption_style(size: int = 12, align: str = "left", colour: str = MUTED) -> str:
    return (
        f"text;html=1;align={align};verticalAlign=middle;fontFamily={FONT};"
        f"fontSize={size};fontColor={colour};strokeColor=none;fillColor=none"
    )


def band_label() -> str:
    return (
        f"text;html=1;align=right;verticalAlign=middle;fontFamily={FONT};"
        f"fontSize=11;fontStyle=1;fontColor={MUTED};strokeColor=none;fillColor=none;"
        f"letterSpacing=1"
    )


def arrow(colour: str, dashed: bool = False, width: float = 1.6) -> str:
    return (
        f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={colour};"
        f"strokeWidth={width};endArrow=blockThin;endFill=1;endSize=6;"
        f"fontFamily={FONT};fontSize=10;fontColor={MUTED};"
        f"labelBackgroundColor=#FFFFFF;{'dashed=1;dashPattern=6 4;' if dashed else ''}"
        f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0"
    )


def label_html(title: str, subtitle: str, detail: str = "") -> str:
    """A three line node label: name, framework, one line of substance."""
    parts = [f"<b style='font-size:14px'>{html.escape(title)}</b>"]
    if subtitle:
        parts.append(
            f"<span style='font-size:10.5px;letter-spacing:0.6px;"
            f"text-transform:uppercase'>{html.escape(subtitle)}</span>"
        )
    if detail:
        parts.append(
            f"<span style='font-size:11px;line-height:1.45'>{html.escape(detail)}</span>"
        )
    return "<div style='padding:2px'>" + "<br/><br/>".join(parts) + "</div>"


# --------------------------------------------------------------------------
# Page 1: architecture
# --------------------------------------------------------------------------


def architecture() -> Page:
    page = Page("Architecture", 1500, 1060)

    left = 210
    right = 1420
    span = right - left

    page.node(
        "AtlasTrip", 60, 40, 600, 34, title_style(24)
    )
    page.node(
        "Five agents on five frameworks, cooperating over the A2A protocol",
        60, 74, 800, 22, caption_style(13),
    )

    # Band labels down the left edge.
    bands = [
        ("CALLER", 150),
        ("ORCHESTRATION", 290),
        ("SPECIALISTS", 500),
        ("TOOL PLANE", 760),
        ("DATA PLANE", 920),
    ]
    for text, y in bands:
        page.node(text, 40, y, 150, 24, band_label())

    # Caller
    client = page.node(
        label_html(
            "Any A2A client",
            "",
            "The CLI, a web app, another agent. It knows one URL and reads one "
            "Agent Card.",
        ),
        left + (span - 420) // 2, 130, 420, 84,
        box("client"),
    )

    # Orchestrator
    concierge = page.node(
        label_html(
            "Concierge",
            "LangGraph",
            "Reads the request, commissions the specialists, renegotiates what "
            "policy rejects, assembles the itinerary.",
        ),
        left + (span - 520) // 2, 268, 520, 118,
        box("orchestrator"),
    )
    page.node(
        ":8000", left + (span - 520) // 2 + 528, 268, 60, 20, caption_style(10)
    )

    # Specialists
    specialists = [
        ("Skyline", "Google ADK", "Sources and ranks flights.", "air", ":8001"),
        ("Hearth", "CrewAI", "Finds a stay near the venue.", "stay", ":8002"),
        ("Sentinel", "LlamaIndex", "Rules on policy and entry.", "policy", ":8003"),
        ("Ledger", "Pydantic AI", "Authorises the spend.", "money", ":8004"),
    ]
    node_w, gap = 272, 34
    total = len(specialists) * node_w + (len(specialists) - 1) * gap
    start = left + (span - total) // 2

    specialist_ids = []
    for index, (name, framework, detail, role, port) in enumerate(specialists):
        x = start + index * (node_w + gap)
        node_id = page.node(
            label_html(name, framework, detail), x, 478, node_w, 132, box(role)
        )
        page.node(port, x, 614, node_w, 18, caption_style(10, "center"))
        specialist_ids.append(node_id)

    # Tool plane
    mcp = page.node(
        label_html(
            "Travel Inventory MCP server",
            "Model Context Protocol, streamable HTTP",
            "search_flights  ·  search_hotels  ·  lookup_employee  ·  "
            "get_cost_center_budget  ·  record_commitment",
        ),
        left + (span - 760) // 2, 740, 760, 112,
        box("tools"),
    )
    page.node(
        ":8100/mcp", left + (span - 760) // 2 + 768, 740, 80, 20, caption_style(10)
    )

    # Data plane
    postgres = page.node(
        label_html(
            "PostgreSQL",
            "",
            "Flights, hotels, people, cost centres, the budget ledger, and the "
            "A2A task store.",
        ),
        left + (span - 700) // 2, 900, 330, 108,
        box("data"),
    )
    tinydb = page.node(
        label_html(
            "TinyDB",
            "",
            "Policy clauses, entry rules, customer sites, and the audit trail.",
        ),
        left + (span - 700) // 2 + 370, 900, 330, 108,
        box("data"),
    )

    # Edges
    page.edge(client, concierge, "A2A  message/stream", arrow("#4C51BF", width=1.8))

    for node_id, (_, _, _, role, _) in zip(specialist_ids, specialists, strict=True):
        page.edge(concierge, node_id, "", arrow(ROLES[role][1]))

    for node_id, (_, _, _, role, _) in zip(specialist_ids, specialists, strict=True):
        page.edge(node_id, mcp, "", arrow(ROLES[role][1], dashed=False, width=1.2))

    page.edge(mcp, postgres, "", arrow("#4A5568"))
    page.edge(mcp, tinydb, "", arrow("#4A5568"))

    # A legend, rather than captions floating over the connectors.
    page.node(
        "", 60, 872, 330, 140,
        f"rounded=1;arcSize=6;html=1;fillColor=#FFFFFF;strokeColor={HAIRLINE};"
        f"strokeWidth=1;dashed=0",
    )
    page.node(
        "<b style='font-size:12px'>Reading this diagram</b>",
        78, 886, 294, 20, caption_style(12, "left", INK),
    )
    page.node(
        "", 80, 924, 30, 2,
        "line;strokeColor=#4C51BF;strokeWidth=2;html=1",
    )
    page.node(
        "<b>A2A</b>&nbsp; agent to agent. One contextId per trip.",
        120, 916, 258, 18, caption_style(10.5, "left", INK),
    )
    page.node(
        "", 80, 956, 30, 2,
        "line;strokeColor=#2C7A7B;strokeWidth=2;html=1",
    )
    page.node(
        "<b>MCP</b>&nbsp; agent to tools. One server, four clients.",
        120, 948, 258, 18, caption_style(10.5, "left", INK),
    )
    page.node(
        "Every agent also persists its A2A tasks to PostgreSQL, and "
        "appends to the audit trail in TinyDB.",
        80, 972, 292, 34, caption_style(10, "left"),
    )

    page.node(
        "MCP gives an agent its tools.&nbsp;&nbsp;A2A lets agents give each "
        "other work.",
        left, 1024, span, 20,
        caption_style(12.5, "center", INK),
    )
    return page


# --------------------------------------------------------------------------
# Page 2: the trip, in order
# --------------------------------------------------------------------------


def sequence() -> Page:
    # The left 330px is reserved for annotations, so nothing ever sits on a
    # lifeline.
    page = Page("Trip sequence", 1820, 1180)
    shift = 330

    page.node("How one trip is booked", 60, 40, 700, 34, title_style(22))
    page.node(
        "Every arrow is an A2A message. All of them carry the same contextId.",
        60, 74, 900, 22, caption_style(13),
    )

    actors = [
        ("Traveller", "client", 90 + shift),
        ("Concierge", "orchestrator", 340 + shift),
        ("Skyline", "air", 610 + shift),
        ("Hearth", "stay", 830 + shift),
        ("Sentinel", "policy", 1050 + shift),
        ("Ledger", "money", 1280 + shift),
    ]

    top = 130
    lifeline_top = top + 62
    lifeline_bottom = 1080

    columns: dict[str, int] = {}
    for name, role, x in actors:
        page.node(
            f"<b>{html.escape(name)}</b>",
            x - 78, top, 156, 46,
            box(role) + ";fontSize=13",
        )
        columns[name] = x
        page.node(
            "",
            x - 1, lifeline_top, 2, lifeline_bottom - lifeline_top,
            f"line;direction=north;strokeColor={HAIRLINE};strokeWidth=1.5;"
            f"dashed=1;dashPattern=4 4;html=1",
        )

    steps = [
        ("Traveller", "Concierge", 230, "Get me to the Kaisei QBR in Tokyo, 14 to 17 October", "#4C51BF", False),
        ("Concierge", "Skyline", 300, "source_flights", "#2B6CB0", False),
        ("Concierge", "Hearth", 340, "source_stay   cap $280 as guidance", "#B7791F", False),
        ("Skyline", "Concierge", 400, "UA 837 / UA 838, premium economy, $3,110.48", "#2B6CB0", True),
        ("Hearth", "Concierge", 440, "Shinagawa Bay Tower, $298.33 a night", "#B7791F", True),
        ("Concierge", "Sentinel", 510, "screen_trip", "#2F855A", False),
        ("Sentinel", "Concierge", 560, "TRV-003 violation: $298.33 against a $280.00 cap", "#C53030", True),
        ("Concierge", "Hearth", 640, "source_stay again, this time enforce_cap=true", "#B7791F", False),
        ("Hearth", "Concierge", 690, "Konan Garden Hotel, $189.96 a night", "#B7791F", True),
        ("Concierge", "Sentinel", 750, "screen_trip", "#2F855A", False),
        ("Sentinel", "Concierge", 795, "within policy, manager approval required", "#2F855A", True),
        ("Concierge", "Ledger", 855, "authorize_spend  $3,688.76", "#B83280", False),
        ("Ledger", "Concierge", 900, "input-required: a human must sign this off", "#B83280", True),
        ("Concierge", "Traveller", 945, "input-required: approve $3,688.76?", "#4C51BF", True),
        ("Traveller", "Concierge", 990, "approve", "#4C51BF", False),
        ("Concierge", "Ledger", 1025, "same task id, with the approval token", "#B83280", False),
        ("Ledger", "Concierge", 1055, "approved, AUTH-351693FF2A, committed", "#B83280", True),
    ]

    for source, target, y, label, colour, is_return in steps:
        x1, x2 = columns[source], columns[target]
        edge_id = page._id()
        dash = "dashed=1;dashPattern=6 4;" if is_return else ""
        page.cells.append(
            f'<mxCell id="{edge_id}" value="{escape(label)}" '
            f'style="html=1;rounded=0;strokeColor={colour};strokeWidth=1.6;'
            f'endArrow={"open" if is_return else "blockThin"};endFill='
            f'{"0" if is_return else "1"};endSize=7;{dash}'
            f'fontFamily={FONT};fontSize=10.5;fontColor={INK};'
            f'labelBackgroundColor=#FFFFFF;verticalAlign=bottom;align=center" '
            f'edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y}" as="targetPoint"/>'
            f"</mxGeometry></mxCell>"
        )

    # The two moments worth calling out.
    page.node(
        "<b>The negotiation</b><br/><br/>Hearth used its judgement, Sentinel "
        "overruled it, and the Concierge asked again rather than deciding for "
        "either of them.<br/><br/>It reads the cap out of Sentinel's finding. "
        "It holds no copy of the policy.",
        60, 560, 250, 170,
        box("note") + ";align=left;fontSize=11;verticalAlign=top;spacing=10",
    )
    page.node(
        "<b>The interrupt</b><br/><br/>Ledger pauses its task. The Concierge "
        "pauses its own.<br/><br/>The question reaches the person who can "
        "answer it without any agent in the chain special-casing the others.",
        60, 850, 250, 170,
        box("note") + ";align=left;fontSize=11;verticalAlign=top;spacing=10",
    )

    page.node(
        "Solid arrows are requests.&nbsp;&nbsp;Dashed arrows are what came back.",
        60, 1120, 700, 20, caption_style(11),
    )
    return page


# --------------------------------------------------------------------------
# Page 3: the A2A task lifecycle
# --------------------------------------------------------------------------


def lifecycle() -> Page:
    """Two rows: the states a task passes through, and the states it ends in.

    Connection points are pinned rather than left to the router, because the
    interesting edges here are short and a router that decides otherwise makes
    the diagram harder to read, not easier.
    """
    page = Page("Task lifecycle", 1180, 780)

    page.node("The A2A task lifecycle", 60, 40, 700, 34, title_style(22))
    page.node(
        "Every agent on this network moves its tasks through these states.",
        60, 74, 900, 22, caption_style(13),
    )

    def state(label: str, detail: str, x: int, y: int, role: str) -> str:
        return page.node(
            f"<b style='font-size:13px'>{html.escape(label)}</b><br/><br/>"
            f"<span style='font-size:10.5px;line-height:1.4'>"
            f"{html.escape(detail)}</span>",
            x, y, 210, 96,
            box(role) + ";align=center",
        )

    page.node("IN FLIGHT", 60, 150, 120, 20, band_label() + ";align=left")
    submitted = state(
        "submitted",
        "The Task object itself, enqueued before anything else.",
        60, 180, "client",
    )
    working = state(
        "working",
        "Status updates carry progress the caller can show a human.",
        420, 180, "orchestrator",
    )
    waiting = state(
        "input-required",
        "Paused, not failed. A human has to answer something.",
        780, 180, "money",
    )

    page.node("TERMINAL", 60, 420, 120, 20, band_label() + ";align=left")
    rejected = state(
        "rejected", "The request itself was wrong.", 60, 450, "stay",
    )
    failed = state(
        "failed", "The request was fine; the work could not be done.",
        300, 450, "stay",
    )
    completed = state(
        "completed", "An artifact was published. Nothing more may be sent.",
        540, 450, "policy",
    )
    canceled = state(
        "canceled", "The caller gave up, or abandoned a waiting task.",
        780, 450, "data",
    )

    def link(
        source: str,
        target: str,
        label: str,
        colour: str,
        exit_x: float,
        exit_y: float,
        entry_x: float,
        entry_y: float,
        dashed: bool = False,
        align: str = "center",
    ) -> None:
        page.edge(
            source,
            target,
            label,
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={colour};"
            f"strokeWidth=1.6;endArrow=blockThin;endFill=1;endSize=7;"
            f"fontFamily={FONT};fontSize=10;fontColor={INK};"
            f"labelBackgroundColor=#FFFFFF;verticalAlign=middle;align={align};"
            f"{'dashed=1;dashPattern=6 4;' if dashed else ''}"
            f"exitX={exit_x};exitY={exit_y};exitDx=0;exitDy=0;"
            f"entryX={entry_x};entryY={entry_y};entryDx=0;entryDy=0",
        )

    link(submitted, working, "start_work()", "#4C51BF", 1, 0.5, 0, 0.5)
    link(working, waiting, "requires_input()", "#B83280", 1, 0.32, 0, 0.32)
    link(
        waiting, working, "a second message,\nsame task id",
        "#B83280", 0, 0.75, 1, 0.75, dashed=True,
    )

    link(submitted, rejected, "reject()", "#B7791F", 0.5, 1, 0.5, 0)
    link(working, failed, "failed()", "#B7791F", 0.35, 1, 0.5, 0)
    link(working, completed, "complete()", "#2F855A", 0.65, 1, 0.5, 0)
    link(waiting, canceled, "cancel()", "#4A5568", 0.5, 1, 0.5, 0)

    page.node(
        "<b>Where each one shows up in AtlasTrip</b><br/><br/>"
        "<b>input-required</b>&nbsp;&nbsp;Ledger, when the spend needs a human. "
        "The Concierge then does the same on its own task, so the question "
        "reaches the person who can answer it.<br/>"
        "<b>rejected</b>&nbsp;&nbsp;A brief that fails validation. The caller "
        "was wrong, so the task is rejected rather than failed.<br/>"
        "<b>failed</b>&nbsp;&nbsp;A route with no inventory. The request was "
        "fine; the work could not be done.",
        60, 610, 1060, 118,
        box("note") + ";align=left;verticalAlign=top;fontSize=11;spacing=12",
    )
    return page


# --------------------------------------------------------------------------


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [architecture(), sequence(), lifecycle()]

    document = (
        '<mxfile host="app.diagrams.net" type="device" '
        'agent="atlastrip-make-diagrams">'
        + "".join(page.render() for page in pages)
        + "</mxfile>"
    )
    target = OUT / "atlastrip.drawio"
    target.write_text(document)
    print(f"Wrote {target} ({len(pages)} pages, {len(document):,} bytes)")
    for page in pages:
        print(f"  {page.name:<16} {page.width} x {page.height}")


if __name__ == "__main__":
    main()
