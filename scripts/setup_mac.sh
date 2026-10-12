#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
[[ -f pyproject.toml && -f app.py ]] || { echo 'Incomplete VIDHAAN project.' >&2; exit 1; }
dependency_profile="${1:-base}"
case "$dependency_profile" in base|dev|embeddings) ;; *) echo 'Choose base, dev or embeddings.' >&2; exit 1;; esac
if command -v python3.12 >/dev/null; then python_command=python3.12; else python_command=python3; fi
"$python_command" -c 'import sys; assert sys.version_info[:2] == (3,12), "Install Python 3.12 (python.org or brew install python@3.12)."'
"$python_command" -m venv .venv
.venv/bin/python -m pip install -r "requirements-$dependency_profile.txt"
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m pip check
if [[ -f data/bundled/manifest.json ]]; then .venv/bin/python -m vidhaan.cli load-bundled; fi
.venv/bin/python -m vidhaan.cli diagnostics
echo 'Setup complete. Launch with bash scripts/run_mac.sh. Normal startup downloads nothing.'
