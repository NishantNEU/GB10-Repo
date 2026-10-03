# shellcheck shell=bash
# Shared settings for every Pitcrew script. Source it; don't run it.
#   source "$(dirname "$0")/env.sh"     (from scripts/)
#   source "$(dirname "$0")/../scripts/env.sh"  (from chaos/)

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$REPO_DIR/.env" ]]; then
  set -a; . "$REPO_DIR/.env"; set +a
fi

: "${KIT_DIR:=$HOME/Desktop/Deploy_starter_kit}"
: "${TOOLSERVER_PORT:=9000}"
: "${VLLM_PORT:=8000}"
: "${PITCREW_DB:=data/pitcrew.db}"
: "${VLLM_IMAGE:=nemoclaw-vllm:qwen36-gb10-arm64}"
: "${VLLM_CONTAINER:=pitcrew-vllm}"
: "${VLLM_SERVED_MODEL:=nvidia/Qwen3.6-35B-A3B-NVFP4}"
: "${VLLM_GPU_MEM_UTIL:=0.5}"
: "${VLLM_MAX_MODEL_LEN:=65536}"
: "${SANDBOX_NAME:=pitcrew}"
: "${HOG_CONTAINER:=pitcrew-test-hog}"
: "${HOG_MEMORY_LIMIT:=32g}"
: "${HOG_STEP_GB:=1}"
: "${HOG_INTERVAL_S:=3}"
: "${HOG_MAX_GB:=30}"
: "${HOG_MIN_FREE_GB:=16}"

[[ "$PITCREW_DB" = /* ]] || PITCREW_DB="$REPO_DIR/$PITCREW_DB"

# Uplink interfaces to close ports on: the current default route plus the (usually down) Ethernet port.
uplink_ifaces() {
  { ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}'
    ip -o link show | awk -F': ' '{print $2}' | grep -E '^(en|eth|wl)' ; } | sort -u
}

say()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }
need_docker() { docker ps >/dev/null 2>&1 || die "no Docker access. Run: sudo usermod -aG docker \$USER, log out/in, then 'tmux kill-server' and start a new tmux."; }
