#!/usr/bin/env bash
# Load the kit's Docker images and make NemoClaw's pinned digest references resolve locally.
# Safe to re-run. Needs Docker access (no sudo).
set -euo pipefail
source "$(dirname "$0")/../env.sh"
need_docker

for f in "$KIT_DIR"/04_container_images/[!.]*.tar.gz; do
  say "docker load $(basename "$f")"
  docker load -i "$f"
done

# NemoClaw's vLLM recipe refers to nvcr.io/nvidia/vllm@sha256:9204569b...; the kit saved it as nemoclaw-vllm.
docker tag "$VLLM_IMAGE" nvcr.io/nvidia/vllm:26.05.post1-py3

say "architecture check (all must be arm64)"
for img in "$VLLM_IMAGE" \
           ghcr.io/nvidia/openshell/supervisor:nemoclaw-v0.0.130-arm64 \
           ghcr.io/nvidia/nemoclaw/openclaw-sandbox:v0.0.130; do
  printf '  %-62s %s\n' "$img" "$(docker image inspect --format '{{.Architecture}}' "$img")"
done

say "digest references NemoClaw uses"
check_ref() {
  if docker image inspect --format '{{.Id}}' "$1" >/dev/null 2>&1; then echo "  OK    $1"
  else echo "  MISS  $1   (NemoClaw will pull it from the registry instead)"; fi
}
check_ref ghcr.io/nvidia/openshell/supervisor@sha256:c8c42aef16c200063e32cbf72e553e4ead027085427b555efafd95063ecead42
check_ref nvcr.io/nvidia/vllm@sha256:9204569b17ee4c0eff75194b8e6e458479c8aee18953b5ab9cf359fcdac659e2

say "GPU inside a container"
docker run --rm --gpus all --entrypoint nvidia-smi "$VLLM_IMAGE" --query-gpu=name,driver_version --format=csv,noheader
