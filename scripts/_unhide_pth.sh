#!/usr/bin/env bash
# Clear the macOS "hidden" flag from the .pth files inside our virtualenvs.
#
# Editable installs work through a .pth file in site-packages. CPython's
# site.py skips any .pth file carrying the macOS UF_HIDDEN flag, without
# logging anything, and the result is that every editable install disappears at
# once with a bare ModuleNotFoundError.
#
# Some macOS setups set that flag on dot-prefixed files: iCloud Desktop and
# Documents sync does it, and so do several endpoint management agents. It can
# come back after it has been cleared, so this runs before anything that needs
# the imports to work rather than only at install time.
#
# On any other platform this is a no-op.
set -uo pipefail

[ "$(uname)" = "Darwin" ] || exit 0

cd "$(dirname "$0")/.."
find . -path '*/site-packages/*.pth' -exec chflags nohidden {} + 2>/dev/null || true
