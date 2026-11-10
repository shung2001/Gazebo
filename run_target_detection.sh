#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${TARGET_DETECTION_PYTHON:-/root/.venvs/we_meet_target/bin/python}"
exec "${python_bin}" "${project_dir}/tools/run_target_detection.py" "$@"
