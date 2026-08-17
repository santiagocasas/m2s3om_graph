#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
uv run uvicorn server.main:app --host 0.0.0.0 --port 7860
