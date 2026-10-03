#!/usr/bin/env bash
# One command to see whether everyone's folders still fit together. Run before every push
# and at each checkpoint in the integration copy (~/GB10-Repo).
#   1. every Python file compiles     2. every shell script parses
#   3. all tests pass, including tests/test_contracts.py (skill <-> tool server <-> policy)
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$REPO_DIR"
PY=.venv/bin/python
rc=0

say "1/3 compile Python"
$PY -m compileall -q common service toolserver dashboard skills chaos tests || rc=1

say "2/3 parse shell scripts"
for f in scripts/*.sh scripts/setup/*.sh chaos/*.sh skills/*.sh; do
  bash -n "$f" || { echo "  syntax error: $f"; rc=1; }
done

say "3/3 tests"
$PY -m pytest -q tests || rc=1

if [[ $rc -eq 0 ]]; then say "ALL GREEN: folders are compatible"; else say "SOMETHING FAILED (see above)"; fi
exit $rc
