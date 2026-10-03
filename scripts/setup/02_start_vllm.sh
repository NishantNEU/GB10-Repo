#!/usr/bin/env bash
# Start Qwen3.6-35B-A3B-NVFP4 on vLLM from the kit's image and weights (no downloads).
# Memory budget: VLLM_GPU_MEM_UTIL (0.5) x ~121 GiB, context VLLM_MAX_MODEL_LEN (65536).
# Run 04_lockdown_ports.sh afterwards: -p 8000:8000 is otherwise open to the venue network.
set -euo pipefail
source "$(dirname "$0")/../env.sh"
need_docker

MODEL_DIR="$KIT_DIR/03_models/Qwen3.6-35B-A3B-NVFP4"
[[ -f "$MODEL_DIR/config.json" ]] || die "model not found at $MODEL_DIR"

if docker ps --format '{{.Names}}' | grep -qx "$VLLM_CONTAINER"; then
  say "$VLLM_CONTAINER already running"; exit 0
fi
docker rm -f "$VLLM_CONTAINER" >/dev/null 2>&1 || true

say "starting $VLLM_CONTAINER (mem util $VLLM_GPU_MEM_UTIL, context $VLLM_MAX_MODEL_LEN)"
docker run -d --name "$VLLM_CONTAINER" --restart unless-stopped \
  --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -p "$VLLM_PORT:8000" \
  -v "$MODEL_DIR":/models/qwen:ro \
  -e HF_HUB_OFFLINE=1 \
  "$VLLM_IMAGE" \
  vllm serve /models/qwen \
    --served-model-name "$VLLM_SERVED_MODEL" \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization "$VLLM_GPU_MEM_UTIL" \
    --max-model-len "$VLLM_MAX_MODEL_LEN" \
    --max-num-seqs 2 --max-num-batched-tokens 4096 \
    --dtype auto --quantization modelopt --kv-cache-dtype fp8 \
    --attention-backend flashinfer --moe-backend marlin \
    --enable-chunked-prefill --enable-prefix-caching \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3

say "waiting for /v1/models (model load takes a few minutes; Ctrl+C is safe, the container keeps going)"
for _ in $(seq 1 180); do
  if curl -sf "localhost:$VLLM_PORT/v1/models" >/dev/null; then
    curl -s "localhost:$VLLM_PORT/v1/models" | jq '.data[] | {id, max_model_len}'
    say "ready. Next: scripts/setup/03_check_vllm.sh"
    exit 0
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx "$VLLM_CONTAINER"; then
    docker logs --tail 40 "$VLLM_CONTAINER"; die "container exited"
  fi
  sleep 5
done
die "not ready after 15 min; check: docker logs -f $VLLM_CONTAINER"
