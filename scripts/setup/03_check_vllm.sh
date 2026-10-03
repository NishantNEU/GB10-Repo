#!/usr/bin/env bash
# Gate before any agent work: context length, a plain answer, and a tool call.
set -uo pipefail
source "$(dirname "$0")/../env.sh"
URL="http://localhost:$VLLM_PORT/v1"
rc=0

ctx=$(curl -sf "$URL/models" | jq -r '.data[0].max_model_len // empty')
if [[ "$ctx" == "$VLLM_MAX_MODEL_LEN" ]]; then say "PASS max_model_len=$ctx"; else say "FAIL max_model_len=${ctx:-unreachable}"; rc=1; fi

ans=$(curl -s "$URL/chat/completions" -H 'Content-Type: application/json' -d "{
  \"model\":\"$VLLM_SERVED_MODEL\",\"max_tokens\":64,
  \"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: pitcrew ok\"}]}" \
  | jq -r '.choices[0].message.content // empty')
if grep -qi 'pitcrew ok' <<<"$ans"; then say "PASS chat: $ans"; else say "FAIL chat: ${ans:-no answer}"; rc=1; fi

tool=$(curl -s "$URL/chat/completions" -H 'Content-Type: application/json' -d "{
  \"model\":\"$VLLM_SERVED_MODEL\",
  \"messages\":[{\"role\":\"user\",\"content\":\"Check current machine memory usage.\"}],
  \"tools\":[{\"type\":\"function\",\"function\":{\"name\":\"get_metrics\",\"description\":\"Get current CPU, memory, disk and GPU metrics\",\"parameters\":{\"type\":\"object\",\"properties\":{}}}}]}" \
  | jq -r '.choices[0].message.tool_calls[0].function.name // empty')
if [[ "$tool" == "get_metrics" ]]; then say "PASS tool call: get_metrics"; else say "FAIL tool call: ${tool:-null} (check: docker logs $VLLM_CONTAINER | grep -i tool)"; rc=1; fi

exit $rc
