#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ $# -eq 0 ]]; then set -- --serve; fi
if [[ -n "${PYTHON_BIN:-}" ]]; then
  exec "$PYTHON_BIN" main.py "$@"
fi
if [[ -x .venv/bin/python ]]; then exec .venv/bin/python main.py "$@"; fi
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    exec "$candidate" main.py "$@"
  fi
done
echo '未找到 Python 3.10+。请安装 Python，或通过 PYTHON_BIN 指定路径。' >&2
exit 1
