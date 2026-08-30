#!/usr/bin/env bash
# Download the model bundles this workspace expects.
# Usage:
#   ./initModels.sh              # show status
#   ./initModels.sh all          # H3 + Music 3 + every LLM
#   ./initModels.sh llm          # every chat LLM
#   ./initModels.sh h3 music3 glm
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
HF_BIN="${HF_BIN:-hf}"

# id|aliases|group|size|repo|relpath
CATALOG=(
  "h3|h3,minimax-h3|h3|103G|appautomaton/minimax-h3-base-8bit-mlx|minimax-h3"
  "music3|music3,minimax-music3|music3|27G|appautomaton/MiniMax-Music3-MLX|minimax-music3"
  "glm|glm,huihui-glm-4.7-flash-abliterated-mlx|llm|17G|huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit|llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit"
  "superqwen|superqwen,superqwen3.8-27b-abliterated-mlx|llm|16G|Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit|llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit"
  "qwen27|qwen27,huihui-qwen3.8-27b-abliterated-mlx|llm|30G|ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit|llms/ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit"
  "gemma|gemma,huihui-gemma-4-31b-it-v2-mlx|llm|34G|thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit|llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit"
  "qwen35|qwen35,huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated-mlx|llm|37G|mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit|llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit"
  "llama70|llama70,llama-3.3-70b-instruct-abliterated-mlx|llm|75G|divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx|llms/divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx"
)

usage() {
  cat <<EOF
Download / resume the local model trees for this workspace.

  $0                 show download status
  $0 status          same
  $0 list            list catalog
  $0 all             H3 + Music 3 + every LLM (~339G)
  $0 llm             every chat LLM (~209G)
  $0 h3              MiniMax H3 MLX 8-bit (~103G)
  $0 music3          MiniMax Music 3 MLX (~27G)
  $0 glm superqwen   one or more catalog ids

Requires the Hugging Face CLI (\`hf\`). Interrupted downloads resume.
Gated repos need \`hf auth login\` first.
EOF
}

need_hf() {
  if ! command -v "$HF_BIN" >/dev/null 2>&1; then
    echo "error: Hugging Face CLI not found (looked for '$HF_BIN')" >&2
    echo "install with: pipx install huggingface_hub[cli]   or   brew install huggingface-cli" >&2
    exit 1
  fi
}

split_row() {
  local row="$1"
  IFS='|' read -r ID ALIASES GROUP SIZE REPO RELPATH <<<"$row"
}

dest_of() {
  echo "$ROOT/$1"
}

model_present() {
  local dir="$1"
  [[ -d "$dir" ]] || return 1
  find "$dir" -type f \( -name '*.safetensors' -o -name '*.gguf' \) -print -quit | grep -q .
}

match_id() {
  local want="$1" row aliases alias
  for row in "${CATALOG[@]}"; do
    split_row "$row"
    if [[ "$want" == "$ID" || "$want" == "$GROUP" ]]; then
      echo "$row"
      return 0
    fi
    IFS=',' read -ra aliases <<<"$ALIASES"
    for alias in "${aliases[@]}"; do
      if [[ "$want" == "$alias" ]]; then
        echo "$row"
        return 0
      fi
    done
  done
  return 1
}

select_rows() {
  local arg row seen=""
  if [[ $# -eq 0 ]]; then
    return 0
  fi
  for arg in "$@"; do
    case "$arg" in
      all)
        for row in "${CATALOG[@]}"; do
          echo "$row"
        done
        ;;
      llm|llms)
        for row in "${CATALOG[@]}"; do
          split_row "$row"
          [[ "$GROUP" == "llm" ]] && echo "$row"
        done
        ;;
      status|list|help|-h|--help)
        echo "error: '$arg' is not a download target" >&2
        exit 1
        ;;
      *)
        if row="$(match_id "$arg")"; then
          echo "$row"
        else
          echo "error: unknown model '$arg'" >&2
          echo "run: $0 list" >&2
          exit 1
        fi
        ;;
    esac
  done
}

print_status() {
  local row dir state
  printf '%-10s %-7s %-6s %-10s %s\n' "ID" "GROUP" "SIZE" "STATE" "REPO"
  for row in "${CATALOG[@]}"; do
    split_row "$row"
    dir="$(dest_of "$RELPATH")"
    if model_present "$dir"; then
      state="present"
    elif [[ -d "$dir" ]]; then
      state="partial"
    else
      state="missing"
    fi
    printf '%-10s %-7s %-6s %-10s %s\n' "$ID" "$GROUP" "$SIZE" "$state" "$REPO"
  done
}

print_list() {
  local row
  printf '%-10s %-7s %-6s %s\n' "ID" "GROUP" "SIZE" "REPO"
  for row in "${CATALOG[@]}"; do
    split_row "$row"
    printf '%-10s %-7s %-6s %s\n' "$ID" "$GROUP" "$SIZE" "$REPO"
  done
}

download_row() {
  local dir
  split_row "$1"
  dir="$(dest_of "$RELPATH")"
  mkdir -p "$dir"
  echo "==> $ID  $REPO  ->  $dir  ($SIZE)"
  "$HF_BIN" download "$REPO" --local-dir "$dir"
}

dedupe_rows() {
  local row id seen="|"
  while IFS= read -r row; do
    [[ -n "$row" ]] || continue
    split_row "$row"
    if [[ "$seen" == *"|$ID|"* ]]; then
      continue
    fi
    seen+="$ID|"
    echo "$row"
  done
}

main() {
  local cmd="${1:-status}"
  case "$cmd" in
    help|-h|--help)
      usage
      ;;
    list)
      print_list
      ;;
    status|"")
      print_status
      ;;
    *)
      need_hf
      local rows row
      rows="$(select_rows "$@" | dedupe_rows)"
      if [[ -z "$rows" ]]; then
        echo "error: nothing to download" >&2
        exit 1
      fi
      while IFS= read -r row; do
        download_row "$row"
      done <<<"$rows"
      echo "done."
      print_status
      ;;
  esac
}

main "$@"
