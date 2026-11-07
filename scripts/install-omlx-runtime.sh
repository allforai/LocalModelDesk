#!/bin/bash
# Optional external runtime; no model weights are downloaded. No app publication.
set -euo pipefail
if [[ $# != 1 || "$1" != /* ]]; then
  echo 'Usage: install-omlx-runtime.sh /absolute/path/to/new/venv' >&2
  exit 2
fi
if [[ -e "$1" ]]; then
  echo 'Refusing to overwrite an existing runtime; choose a new directory.' >&2
  exit 1
fi
uv venv --python 3.13 --seed "$1"
# Official audited source. Build native Metal kernels; full Xcode is required.
OMLX_WITH_CUSTOM_KERNEL=1 uv pip install --python "$1/bin/python" \
  'omlx @ git+https://github.com/jundot/omlx.git@2165e75726ba83d9651dbaced61c97728da77bba'
"$1/bin/python" -I -c 'from omlx.custom_kernels import native_kernel_status; s=native_kernel_status(); failed={k:v for k,v in s.items() if not v["available"]}; print(failed or "All native kernels available"); raise SystemExit(bool(failed))'
echo "Set oMLX Python in LocalModelDesk settings to: $1/bin/python"
