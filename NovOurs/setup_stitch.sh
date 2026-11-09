#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f NovOurs/.local/upstream/stitch/requirements.txt || python3 NovOurs/setup_upstream.py
lifesim-venv/bin/python -m venv --system-site-packages NovOurs/.local/stitch-venv
NovOurs/.local/stitch-venv/bin/pip install -r NovOurs/.local/upstream/stitch/requirements.txt 'dspy-ai==2.6.27' 'dspy==3.4.1' 'litellm==1.74.15'
