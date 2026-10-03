#!/usr/bin/env bash
# Read-only sanity check for the GB10 machine and the offline Deploy Starter Kit.
# Prints PASS / WARN / FAIL per check and keeps going after failures.
# Never installs, deletes, edits config, or uses sudo.
#
# Usage: scripts/sanity_check.sh [--no-checksums]
#   KIT_DIR=/path/to/kit scripts/sanity_check.sh

set -uo pipefail

KIT_DIR="${KIT_DIR:-$HOME/Desktop/Deploy_starter_kit}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DO_CHECKSUMS=1
[[ "${1:-}" == "--no-checksums" ]] && DO_CHECKSUMS=0

EXP_NODE="22.22.1"
EXP_OLLAMA="0.35.0"
EXP_OPENSHELL="0.0.116"
EXP_NEMOCLAW="0.0.130"
EXP_OPENCLAW="2026.9.2"

N_PASS=0 N_WARN=0 N_FAIL=0
if [[ -t 1 ]]; then G=$'\e[32m' Y=$'\e[33m' R=$'\e[31m' B=$'\e[1m' Z=$'\e[0m'; else G="" Y="" R="" B="" Z=""; fi

pass()    { N_PASS=$((N_PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$Z" "$*"; }
warn()    { N_WARN=$((N_WARN+1)); printf '  %sWARN%s  %s\n' "$Y" "$Z" "$*"; }
fail()    { N_FAIL=$((N_FAIL+1)); printf '  %sFAIL%s  %s\n' "$R" "$Z" "$*"; }
info()    { printf '  INFO  %s\n' "$*"; }
section() { printf '\n%s== %s ==%s\n' "$B" "$*" "$Z"; }
have()    { command -v "$1" >/dev/null 2>&1; }
# Run with a timeout so a hung daemon can't stall the script.
t()       { timeout 15 "$@"; }
indent()  { sed 's/^/        /'; }
# First x.y.z-looking token in a string.
ver_of()  { grep -oE '[0-9]+\.[0-9]+\.[0-9]+' <<<"$1" | head -1; }

# ---------------------------------------------------------------------------
section "1. System"

arch="$(uname -m)"
[[ "$arch" == "aarch64" ]] && pass "arch: $arch" || fail "arch: $arch (expected aarch64)"

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  info "OS: ${PRETTY_NAME:-unknown}  kernel: $(uname -r)"
  [[ "${VERSION_ID:-}" == "24.04" ]] && pass "Ubuntu 24.04" || warn "OS version ${VERSION_ID:-?} (expected Ubuntu 24.04)"
fi
[[ -r /etc/dgx-release ]] && info "DGX OS: $(grep -E 'DGX_SWBUILD_VERSION|DGX_OTA_VERSION' /etc/dgx-release | tr '\n' ' ')"

free -h | indent
mem_gb=$(free -g | awk '/^Mem:/{print $2}')
(( mem_gb >= 100 )) && pass "memory: ${mem_gb} GiB total" || warn "memory: ${mem_gb} GiB total (expected ~121)"

home_free=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
(( home_free >= 100 )) && pass "disk free in ~: ${home_free} GiB" || warn "disk free in ~: ${home_free} GiB (want >=100 for images + models)"
if [[ -d "$KIT_DIR" ]]; then
  kit_dev=$(df --output=source "$KIT_DIR" | tail -1)
  kit_free=$(df -BG --output=avail "$KIT_DIR" | tail -1 | tr -dc '0-9')
  pass "disk free on kit drive ($kit_dev): ${kit_free} GiB"
fi

if have nvidia-smi && t nvidia-smi >/dev/null 2>&1; then
  pass "nvidia-smi works"
  gpu=$(t nvidia-smi --query-gpu=name,driver_version --format=csv,noheader)
  cuda=$(t nvidia-smi | grep -oE 'CUDA Version: [0-9.]+' | awk '{print $3}')
  info "GPU, driver: $gpu"
  info "CUDA (driver-supported): ${cuda:-unknown}"
  [[ "$gpu" == *GB10* ]] && pass "GPU is GB10" || warn "GPU is not GB10: $gpu"
  have nvcc && info "nvcc: $(nvcc --version | grep -oE 'release [0-9.]+')"
else
  fail "nvidia-smi missing or not working"
fi

# ---------------------------------------------------------------------------
section "2. Docker"

DOCKER_OK=0
if have docker; then
  pass "docker installed: $(docker --version 2>/dev/null)"
  if systemctl is-active --quiet docker 2>/dev/null; then
    pass "docker daemon: active (systemd)"
  else
    fail "docker daemon not active (systemctl is-active docker = $(systemctl is-active docker 2>/dev/null))"
  fi
  if id -nG | tr ' ' '\n' | grep -qx docker; then
    pass "user $(id -un) is in the docker group (current session)"
  elif getent group docker | grep -qw "$(id -un)"; then
    warn "user is in the docker group in /etc/group but not this session (log out/in or run: newgrp docker)"
  else
    fail "user $(id -un) is NOT in the docker group"
  fi
  if out=$(t docker ps 2>&1); then
    DOCKER_OK=1
    pass "docker ps works without sudo"
  else
    fail "docker ps without sudo: $(head -1 <<<"$out")"
  fi
  if [[ -r /etc/docker/daemon.json ]]; then
    info "/etc/docker/daemon.json:"
    indent </etc/docker/daemon.json
    # NemoClaw 0.0.130 preflight.ts:865: OpenShell sets host cgroupns on its own container.
    if grep -q '"default-cgroupns-mode"' /etc/docker/daemon.json; then
      info "cgroupns set: $(grep -oE '"default-cgroupns-mode"[^,}]*' /etc/docker/daemon.json)"
    else
      info "default-cgroupns-mode not set (fine: NemoClaw 0.0.130 no longer requires it)"
    fi
    grep -q 'nvidia' /etc/docker/daemon.json && info "nvidia runtime referenced in daemon.json" \
      || info "nvidia runtime not in daemon.json (GPU access goes through CDI instead)"
  elif [[ -e /etc/docker/daemon.json ]]; then
    warn "/etc/docker/daemon.json exists but is not readable by $(id -un)"
  else
    info "/etc/docker/daemon.json does not exist (defaults; cgroupns not required by NemoClaw 0.0.130)"
  fi
  if have nvidia-ctk; then
    pass "nvidia container toolkit: $(nvidia-ctk --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    cdi=$(nvidia-ctk cdi list 2>/dev/null | grep -c '^nvidia.com/gpu=')
    (( cdi > 0 )) && pass "CDI spec lists $cdi nvidia.com/gpu device(s)" || fail "no CDI GPU devices (nvidia-ctk cdi list)"
  else
    fail "nvidia-ctk (NVIDIA Container Toolkit) missing"
  fi
  if (( DOCKER_OK )); then
    imgs=$(t docker images --format '{{.Repository}}:{{.Tag}}' | grep -v '<none>')
    if [[ -z "$imgs" ]]; then
      warn "no docker images loaded"
    else
      info "loaded images (repo:tag  arch):"
      while read -r img; do
        a=$(t docker image inspect --format '{{.Architecture}}' "$img" 2>/dev/null)
        printf '        %-70s %s\n' "$img" "$a"
        [[ "$a" == "arm64" ]] || warn "image $img is $a, not arm64"
      done <<<"$imgs"
    fi
  else
    warn "skipping image list/arch check (no docker access)"
  fi
else
  fail "docker not installed"
fi

# ---------------------------------------------------------------------------
section "3. Node and npm"

if have node; then
  nv=$(node --version | tr -d v)
  [[ "$nv" == "$EXP_NODE" ]] && pass "node $nv" \
    || { [[ "$(printf '%s\n22.19.0\n' "$nv" | sort -V | head -1)" == "22.19.0" ]] \
           && warn "node $nv (kit ships $EXP_NODE; >=22.19 is OK)" \
           || fail "node $nv (NemoClaw needs >=22.19; kit ships $EXP_NODE)"; }
  info "node path: $(command -v node)"
else
  fail "node not installed (kit ships $EXP_NODE)"
fi
if have npm; then
  npv=$(npm --version 2>/dev/null)
  [[ "${npv%%.*}" -ge 10 ]] 2>/dev/null && pass "npm $npv" || fail "npm $npv (need >=10)"
else
  fail "npm not installed"
fi

# ---------------------------------------------------------------------------
section "4. Ollama"

if have ollama; then
  ov=$(ver_of "$(t ollama --version 2>&1)")
  [[ "$ov" == "$EXP_OLLAMA" ]] && pass "ollama $ov" || warn "ollama ${ov:-unknown} (kit ships $EXP_OLLAMA)"
  st=$(systemctl is-active ollama 2>/dev/null)
  [[ "$st" == "active" ]] && pass "ollama service: active" || warn "ollama service: ${st:-not found}"
  if out=$(t ollama list 2>&1); then
    info "ollama list:"; indent <<<"$out"
    grep -q 'qwen3.5:9b' <<<"$out" && pass "qwen3.5:9b present" || warn "qwen3.5:9b not in ollama store (kit has it in 03_models/ollama)"
  else
    warn "ollama list failed: $(head -1 <<<"$out")"
  fi
else
  warn "ollama not installed (kit ships $EXP_OLLAMA; only needed for the Ollama path)"
fi

# ---------------------------------------------------------------------------
section "5. vLLM"

if (( DOCKER_OK )); then
  vimg=$(t docker images --format '{{.Repository}}:{{.Tag}}' | grep -iE 'vllm')
  [[ -n "$vimg" ]] && pass "vLLM image(s) loaded: $(tr '\n' ' ' <<<"$vimg")" \
    || fail "no vLLM image loaded (kit: 04_container_images/nemoclaw-vllm-qwen36-gb10-arm64.tar.gz)"
  vrun=$(t docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep -iE 'vllm')
  [[ -n "$vrun" ]] && info "running vLLM container(s): $vrun" || info "no vLLM container running"
else
  warn "cannot check vLLM image/containers (no docker access)"
fi
if out=$(curl -s --max-time 3 http://localhost:8000/v1/models 2>/dev/null) && [[ -n "$out" ]]; then
  info "something answers on localhost:8000/v1/models: $(head -c 200 <<<"$out")"
fi

# ---------------------------------------------------------------------------
section "6. OpenShell"

if have openshell; then
  osv=$(ver_of "$(t openshell --version 2>&1)")
  info "openshell path: $(command -v openshell)"
  if [[ "$osv" == "$EXP_OPENSHELL" ]]; then
    warn "openshell $osv (matches kit binaries, but kit supervisor image is 0.0.130 - see investigation A)"
  else
    info "openshell ${osv:-unknown} (kit binaries $EXP_OPENSHELL, kit supervisor image 0.0.130)"
    pass "openshell on PATH"
  fi
  have openshell-gateway && info "openshell-gateway: $(command -v openshell-gateway)"
else
  warn "openshell not on PATH (kit binaries: 01_installers/openshell-v$EXP_OPENSHELL-linux-arm64)"
fi

# ---------------------------------------------------------------------------
section "7. NemoClaw and OpenClaw"

if have nemoclaw; then
  ncv=$(ver_of "$(t nemoclaw --version 2>&1)")
  [[ "$ncv" == "$EXP_NEMOCLAW" ]] && pass "nemoclaw $ncv" || warn "nemoclaw ${ncv:-unknown} (kit is $EXP_NEMOCLAW)"
else
  warn "nemoclaw not installed (kit: 02_repos/NemoClaw-v$EXP_NEMOCLAW-prepared-linux-arm64.tar.gz)"
fi
if have openclaw; then
  ocv=$(ver_of "$(t openclaw --version 2>&1)")
  [[ "$ocv" == "$EXP_OPENCLAW" ]] && pass "openclaw $ocv" || warn "openclaw ${ocv:-unknown} (kit pins $EXP_OPENCLAW)"
else
  info "openclaw not on host PATH (normal: NemoClaw runs it inside the sandbox image)"
fi
for d in "$HOME/.nemoclaw" "$HOME/.openclaw" "$HOME/.config/openshell" "$HOME/.openshell"; do
  if [[ -d "$d" ]]; then info "$d exists: $(ls -A "$d" | head -10 | tr '\n' ' ')"; else info "$d: absent"; fi
done

# ---------------------------------------------------------------------------
section "8. Python"

if have python3; then
  pyv=$(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')
  [[ "$pyv" == 3.12.* ]] && pass "python3 $pyv (matches kit wheels cp312)" || warn "python3 $pyv (kit wheels are cp312)"
  info "python3 path: $(command -v python3)"
  [[ -x /usr/bin/python3 ]] && pass "/usr/bin/python3 exists (NemoClaw sanitizer trusted path)" || warn "/usr/bin/python3 missing"
  if python3 -m pip --version >/dev/null 2>&1; then pass "pip: $(python3 -m pip --version | cut -d' ' -f1-2)"
  else warn "pip not available for python3"; fi
  if python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then pass "venv + ensurepip available"
  else fail "venv/ensurepip missing (python3 -m venv will fail)"; fi
else
  fail "python3 not installed"
fi

# ---------------------------------------------------------------------------
section "9. git, tmux, repo"

have git  && pass "git $(git --version | awk '{print $3}')" || fail "git not installed"
have tmux && pass "tmux $(tmux -V | awk '{print $2}')"     || warn "tmux not installed"
for tool in zstd strings curl jq lsof; do
  have "$tool" && pass "$tool present" || warn "$tool missing"
done
if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  info "repo: $REPO_DIR"
  info "remote: $(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || echo none)"
  info "branch: $(git -C "$REPO_DIR" branch --show-current)"
  if git -C "$REPO_DIR" rev-parse HEAD >/dev/null 2>&1; then
    info "HEAD: $(git -C "$REPO_DIR" log -1 --format='%h %s')"
  else
    warn "repo has no commits yet"
  fi
fi

# ---------------------------------------------------------------------------
section "10. Kit"

if [[ ! -d "$KIT_DIR" ]]; then
  fail "kit not found at $KIT_DIR"
else
  pass "kit found: $KIT_DIR"
  info "total size: $(du -sh "$KIT_DIR" 2>/dev/null | cut -f1)"
  info "layout:"
  (cd "$KIT_DIR" && du -sh -- [!.]*/ 2>/dev/null) | indent

  n_dot=$(find "$KIT_DIR" -name '._*' 2>/dev/null | wc -l)
  (( n_dot == 0 )) && pass "no macOS ._* files" || warn "$n_dot macOS ._* AppleDouble files in kit"
  risky=$(find "$KIT_DIR/01_installers/python-wheels-linux-arm64-py312" \
               "$KIT_DIR/01_installers/npm-cache" \
               "$KIT_DIR/01_installers/nemoclaw-v0.0.130-npm-cache" \
               "$KIT_DIR/01_installers/nemoclaw-v0.0.130-npm-packages" \
               "$KIT_DIR/01_installers/npm-linux-arm64" \
               "$KIT_DIR/03_models/ollama" \
               -name '._*' 2>/dev/null)
  if [[ -n "$risky" ]]; then
    warn "$(wc -l <<<"$risky") ._* files inside wheel/npm-cache/ollama-store folders (installers may choke)"
    info "count by folder:"
    sed "s|$KIT_DIR/||" <<<"$risky" | awk -F/ '{print $1"/"$2"/"$3}' | sort | uniq -c | indent
    info "examples:"
    sed "s|$KIT_DIR/||" <<<"$risky" | grep -v '_cacache/' | head -10 | indent
  else
    pass "no ._* files inside wheel/npm-cache/ollama-store folders"
  fi
  # ._ entries inside tarballs get extracted too.
  tar_dots=$(tar tzf "$KIT_DIR/02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz" 2>/dev/null | grep -c '/\._\|^\._')
  (( tar_dots == 0 )) && pass "NemoClaw prepared tarball has no ._* entries" \
    || warn "NemoClaw prepared tarball contains $tar_dots ._* entries (extract with --exclude='._*')"

  demo="$KIT_DIR/08_demo_backup"
  if [[ -d "$demo" ]]; then
    [[ -z "$(ls -A "$demo")" ]] && pass "08_demo_backup is empty (as expected)" || warn "08_demo_backup not empty: $(ls -A "$demo" | tr '\n' ' ')"
  else
    warn "08_demo_backup missing"
  fi

  if (( DO_CHECKSUMS )); then
    shopt -s nullglob
    for f in "$KIT_DIR"/07_checksums/[!.]*.sha256; do
      want=$(awk '{print $1}' "$f")
      # Checksum files hold macOS paths; map them back into the kit.
      rel=$(awk '{ $1=""; sub(/^ +/,""); print }' "$f" | sed -E 's|.*/(0[0-9]_[^/]+/.*)$|\1|')
      target="$KIT_DIR/$rel"
      if [[ ! -f "$target" ]]; then fail "checksum target missing: $rel"; continue; fi
      got=$(sha256sum "$target" | awk '{print $1}')
      [[ "$got" == "$want" ]] && pass "sha256 OK: $rel" || fail "sha256 MISMATCH: $rel"
    done
    sumfile="$KIT_DIR/01_installers/node-v22.22.1-linux-arm64/SHASUMS256.txt"
    tarball="$KIT_DIR/01_installers/node-v22.22.1-linux-arm64/node-v22.22.1-linux-arm64.tar.xz"
    if [[ -f "$sumfile" && -f "$tarball" ]]; then
      want=$(grep ' node-v22.22.1-linux-arm64.tar.xz$' "$sumfile" | awk '{print $1}')
      got=$(sha256sum "$tarball" | awk '{print $1}')
      [[ -n "$want" && "$got" == "$want" ]] && pass "sha256 OK: node tarball" || fail "sha256 MISMATCH: node tarball"
    fi
    for cs in "$KIT_DIR"/01_installers/openshell-v0.0.116-linux-arm64/[!.]*checksums-sha256.txt; do
      while read -r want name; do
        name=${name#\*}
        p="$KIT_DIR/01_installers/openshell-v0.0.116-linux-arm64/$name"
        [[ -f "$p" ]] || continue
        got=$(sha256sum "$p" | awk '{print $1}')
        [[ "$got" == "$want" ]] && pass "sha256 OK: openshell/$name" || fail "sha256 MISMATCH: openshell/$name"
      done <"$cs"
    done
    shopt -u nullglob
  else
    info "checksums skipped (--no-checksums)"
  fi
fi

# ---------------------------------------------------------------------------
section "Summary"
printf '  PASS %d   WARN %d   FAIL %d\n' "$N_PASS" "$N_WARN" "$N_FAIL"
exit 0
