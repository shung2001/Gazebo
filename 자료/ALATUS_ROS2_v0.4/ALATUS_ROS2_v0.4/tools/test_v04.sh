#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/alatus_runtime:$PWD/src/alatus_vision:$PWD/src/alatus_mavros${PYTHONPATH:+:$PYTHONPATH}"
python3 -m compileall -q src tools tests integration
python3 -m pytest -q tests
python3 regression/v03/tools/run_local_tests.py
