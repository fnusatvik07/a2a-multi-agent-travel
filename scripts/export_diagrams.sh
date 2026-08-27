#!/usr/bin/env bash
# Renders docs/diagrams/atlastrip.drawio to PNG, one file per page.
#
# PNG only: draw.io's SVG export embeds a base64 raster fallback for every text
# block, which triples the file size for no benefit here. The .drawio file is
# the editable source if you want vectors.
#
# Needs the draw.io desktop app on PATH:  brew install --cask drawio
set -euo pipefail

cd "$(dirname "$0")/.."
python3 scripts/make_diagrams.py

DIAGRAMS="docs/diagrams"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# The exporter's --page-index is unreliable across versions, so each page is
# split into its own single-page file first.
python3 - "$DIAGRAMS/atlastrip.drawio" "$WORK" <<'PY'
import pathlib, re, sys

source, work = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
pages = re.findall(r"<diagram .*?</diagram>", source.read_text(), re.DOTALL)
for name, page in zip(["architecture", "trip-sequence", "task-lifecycle"], pages):
    (work / f"{name}.drawio").write_text(
        '<mxfile host="app.diagrams.net" type="device">' + page + "</mxfile>"
    )
PY

for name in architecture trip-sequence task-lifecycle; do
  drawio --export --format png --scale 2 --border 20 \
    --output "$DIAGRAMS/$name.png" "$WORK/$name.drawio" >/dev/null 2>&1
  printf '  %-16s %s\n' "$name" "$(du -h "$DIAGRAMS/$name.png" | cut -f1)"
done
