#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${HAILO_PYTHON:-/root/.venvs/we_meet_hailo8/bin/python}"

if ! "$PYTHON_BIN" -c 'import hailo_sdk_client' 2>/dev/null; then
  echo 'Hailo Dataflow Compiler 3.x is not installed in the selected Python environment.' >&2
  echo 'Download the Hailo-8/8L Linux x86_64 DFC from Hailo Developer Zone and install its wheel.' >&2
  exit 1
fi

"$PYTHON_BIN" -c 'from ultralytics.data.utils import check_det_dataset; check_det_dataset("calibration_data.yaml")'

"$PYTHON_BIN" export_hailo8.py
"$PYTHON_BIN" compile_saved_har.py
