#!/usr/bin/env bash
set -euo pipefail
# Read-only reuse of tim; no pip/conda modifications.
export CUDA_VISIBLE_DEVICES="${NOVOURS_GPU:-0}"
export VLLM_USE_V2_MODEL_RUNNER=0
export VLLM_USE_FLASHINFER_SAMPLER=0
exec "${NOVOURS_VLLM:-/home/tim/miniconda3/envs/tim/bin/vllm}" serve "${NOVOURS_MODEL_PATH:-/mnt/data/Qwen3-8B}" \
  --served-model-name "${NOVOURS_MODEL_NAME:-Qwen3-8B}" --host 127.0.0.1 --port "${NOVOURS_PORT:-8011}" \
  --max-model-len "${NOVOURS_CONTEXT:-32768}" --gpu-memory-utilization "${NOVOURS_GPU_MEMORY:-0.93}" --max-num-seqs "${NOVOURS_SEQUENCES:-8}" --enforce-eager \
  --enable-auto-tool-choice --tool-call-parser hermes --reasoning-parser qwen3
