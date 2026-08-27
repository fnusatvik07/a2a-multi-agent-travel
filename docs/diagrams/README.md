# Diagrams

Three pages, generated from `scripts/make_diagrams.py` rather than drawn by
hand, so the geometry is exact and a change to the architecture means editing
one file instead of nudging boxes.

| | |
|---|---|
| [`architecture.png`](architecture.png) | What talks to what: the caller, the orchestrator, the four specialists, the MCP server, the two stores |
| [`trip-sequence.png`](trip-sequence.png) | What happens in order, including the renegotiation with Hearth and the approval interrupt |
| [`task-lifecycle.png`](task-lifecycle.png) | The A2A task states, and where each one shows up in this project |

`atlastrip.drawio` is the editable source, one page per diagram. Open it at
[app.diagrams.net](https://app.diagrams.net) or in the draw.io desktop app.

## Regenerating

```bash
./scripts/export_diagrams.sh
```

That rebuilds the `.drawio` file and re-exports a PNG for every page. It
needs the draw.io desktop app on your PATH:

```bash
brew install --cask drawio
```

Editing the `.drawio` file directly works too, but the next run of the export
script will overwrite it. Change `scripts/make_diagrams.py` instead if you want
the edit to stick.
