#!/usr/bin/env bash
# Return the demo to "healthy" in under 60 s:
#   remove the test hog, clear jobs/metrics/incidents/approvals (customers stay),
#   restart the sample service and detector, wait for /health == healthy.
set -euo pipefail
source "$(dirname "$0")/env.sh"
need_docker
t0=$(date +%s)

docker rm -f "$HOG_CONTAINER" >/dev/null 2>&1 && say "removed $HOG_CONTAINER" || say "no $HOG_CONTAINER running"

# Stop service + detector first so nothing writes while the tables are cleared.
tmux kill-window -t pitcrew:service 2>/dev/null || true
tmux kill-window -t pitcrew:detector 2>/dev/null || true
rm -f "$REPO_DIR/run/service_status.json"
(cd "$REPO_DIR" && .venv/bin/python -m service.seed --reset)

"$REPO_DIR/scripts/run_all.sh"   # starts whatever isn't running (service, detector, tool server)

say "waiting for healthy"
for _ in $(seq 1 55); do
  status=$(curl -sf -m 2 "localhost:$TOOLSERVER_PORT/health" | jq -r '.status // empty' 2>/dev/null || true)
  if [[ "$status" == healthy ]]; then
    say "healthy after $(( $(date +%s) - t0 ))s"; exit 0
  fi
  sleep 1
done
die "not healthy after $(( $(date +%s) - t0 ))s (last status: ${status:-no answer from :$TOOLSERVER_PORT/health})"
