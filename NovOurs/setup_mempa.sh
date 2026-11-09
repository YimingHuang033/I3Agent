#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
lifesim-venv/bin/python -m venv --system-site-packages NovOurs/.local/venv
NovOurs/.local/venv/bin/pip install 'mcp==1.30.0' 'json-repair==0.64.8'
