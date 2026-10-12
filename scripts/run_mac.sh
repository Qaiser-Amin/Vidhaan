#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
[[ -x .venv/bin/python && -f app.py ]] || { echo 'Run bash scripts/setup_mac.sh first.' >&2; exit 1; }
export VIDHAAN_PROFILE="${1:-evidence_only}"
case "$VIDHAAN_PROFILE" in evidence_only|lenovo_cpu|mac_m5) ;; *) echo 'Unknown hardware profile.' >&2; exit 1;; esac
if [[ -f data/bundled/manifest.json ]]; then .venv/bin/python -m vidhaan.cli load-bundled; fi
exec .venv/bin/python app.py
