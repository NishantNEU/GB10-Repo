#!/usr/bin/env bash
# Install OpenShell 0.0.116 (user-local, from the kit) and NemoClaw 0.0.130 (kit's prepared tarball).
# NemoClaw 0.0.130 requires exactly OpenShell 0.0.116 (blueprint.yaml:6-7; see SANITY_REPORT.md §A).
# The NemoClaw installer is interactive and may ask for sudo. If it jumps into onboarding, Ctrl+C:
# onboard with scripts/setup/06_onboard.md once vLLM passes 03_check_vllm.sh.
set -euo pipefail
source "$(dirname "$0")/../env.sh"
need_docker

OS_DIR="$KIT_DIR/01_installers/openshell-v0.0.116-linux-arm64"
mkdir -p "$HOME/.local/bin"
for t in openshell-aarch64-unknown-linux-musl openshell-gateway-aarch64-unknown-linux-gnu \
         openshell-sandbox-aarch64-unknown-linux-musl; do
  say "extract $t"
  tar xzf "$OS_DIR/$t.tar.gz" -C "$HOME/.local/bin"
done
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  export PATH="$HOME/.local/bin:$PATH"
  grep -q 'HOME/.local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
esac
v=$(openshell --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
[[ "$v" == "0.0.116" ]] || die "openshell reports '$v', expected 0.0.116"
say "openshell $v"

if [[ ! -d "$HOME/NemoClaw" ]]; then
  say "extract NemoClaw 0.0.130 (skipping 44k macOS ._ files)"
  tar xzf "$KIT_DIR/02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz" -C "$HOME" --exclude='._*'
fi
[[ -f "$HOME/NemoClaw/install.sh" ]] || die "expected $HOME/NemoClaw/install.sh"
say "running the NemoClaw installer (interactive)"
cd "$HOME/NemoClaw" && bash install.sh
say "nemoclaw $(nemoclaw --version 2>&1 | head -1)"
