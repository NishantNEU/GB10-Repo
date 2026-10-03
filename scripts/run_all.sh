#!/usr/bin/env bash
# Start (or restart) the host-side Pitcrew processes in tmux session "pitcrew".
#   scripts/run_all.sh            start every window that isn't running
#   scripts/run_all.sh restart service detector    restart named windows
# Entry commands belong to their owners; override them in .env if they differ.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$REPO_DIR"

PY="$REPO_DIR/.venv/bin/python"
: "${SERVICE_CMD:=$PY -m service.sample_service}"
: "${DETECTOR_CMD:=$PY -m service.detector}"
: "${TOOLSERVER_CMD:=$REPO_DIR/.venv/bin/uvicorn toolserver.app:app --host ${TOOLSERVER_HOST:-0.0.0.0} --port $TOOLSERVER_PORT}"
declare -A CMDS=([toolserver]="$TOOLSERVER_CMD" [service]="$SERVICE_CMD" [detector]="$DETECTOR_CMD")
ORDER=(toolserver service detector)
SESSION=pitcrew
mkdir -p logs

start_window() {
  local w=$1 cmd=${CMDS[$1]}
  tmux kill-window -t "$SESSION:$w" 2>/dev/null || true
  # Keep the pane open after a crash so the traceback stays visible; tee to logs/<window>.log.
  tmux new-window -d -t "$SESSION" -n "$w" "cd '$REPO_DIR' && $cmd 2>&1 | tee -a logs/$w.log; echo '[exited]'; exec bash"
  say "started $w: $cmd"
}

tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" -n shell -c "$REPO_DIR"

if [[ "${1:-}" == restart ]]; then
  shift; for w in "$@"; do start_window "$w"; done
else
  for w in "${ORDER[@]}"; do
    tmux list-windows -t "$SESSION" -F '#W' | grep -qx "$w" || start_window "$w"
  done
fi
say "attach with: tmux attach -t $SESSION"
