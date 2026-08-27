#!/usr/bin/env bash
# Runs each unit test suite inside the virtualenv of the thing it tests.
#
# There is no single environment that can import all five agents at once, so
# there is no single pytest run either. That is a consequence of the
# architecture, not a workaround for it.
set -uo pipefail

cd "$(dirname "$0")/.."
./scripts/_unhide_pth.sh

CORE_SRC="$PWD/packages/atlastrip_core/src"

# name : virtualenv : source root : test path
declare -a SUITES=(
  "core:packages/atlastrip_core/.venv:packages/atlastrip_core/src:tests/core"
  "skyline:agents/skyline_adk/.venv:agents/skyline_adk/src:tests/agents/skyline"
  "hearth:agents/hearth_crewai/.venv:agents/hearth_crewai/src:tests/agents/hearth"
  "sentinel:agents/sentinel_llamaindex/.venv:agents/sentinel_llamaindex/src:tests/agents/sentinel"
  "ledger:agents/ledger_pydanticai/.venv:agents/ledger_pydanticai/src:tests/agents/ledger"
  "concierge:agents/concierge_langgraph/.venv:agents/concierge_langgraph/src:tests/agents/concierge"
)

failed=0
for suite in "${SUITES[@]}"; do
  IFS=: read -r name venv src path <<< "$suite"
  printf '\n\033[1m%s\033[0m  (%s)\n' "$name" "$venv"
  # PYTHONPATH is belt and braces. The editable installs already put these on
  # the path; see scripts/_unhide_pth.sh for the macOS failure mode where they
  # silently stop doing so.
  if ! PYTHONPATH="$CORE_SRC:$PWD/$src" \
       "$venv/bin/python" -m pytest "$path" -q -p no:cacheprovider; then
    failed=1
  fi
done

echo
if [ "$failed" -eq 0 ]; then
  echo "All unit suites passed."
else
  echo "At least one unit suite failed."
fi
exit "$failed"
