#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${HERE}/minimax-h3"
OUT_DIR="${HERE}/outputs"
mkdir -p "$OUT_DIR"
PROMPT="${1:-A cinematic shot of rain on a quiet city street at night, neon reflections, stereo ambience.}"
"${HERE}/unload-llm.sh"
STAMP=$(date +%Y%m%d-%H%M%S)
exec mlx-h3 "$PROMPT" \
  --tokenizer "${ROOT}/tokenizer/tokenizer.json" \
  --text-encoder "${ROOT}/mlx-8bit/te_qwen3vl_a8g32.safetensors" \
  --dit "${ROOT}/mlx-8bit/dit_fl2va_a8g32.safetensors" \
  --ref-dit "${ROOT}/mlx-8bit/dit_ref2va_a8g32.safetensors" \
  --video-vae "${ROOT}/bf16/vae/minimax_h3_video_vae_fp16.safetensors" \
  --audio-vae "${ROOT}/bf16/vae/minimax_h3_audio_vae_fp32.safetensors" \
  --width 512 \
  --height 288 \
  --frames 124 \
  --steps 20 \
  --budget 70 \
  --output "${OUT_DIR}/h3-${STAMP}.mp4"
