#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${HAILO_PYTHON:-/root/.venvs/we_meet_hailo8/bin/python}"
"$PYTHON_BIN" -c 'import hailo_sdk_client; from ultralytics.data.utils import check_det_dataset; check_det_dataset("calibration_data.yaml")'
"$PYTHON_BIN" export_hailo8.py
"$PYTHON_BIN" compile_saved_har.py
