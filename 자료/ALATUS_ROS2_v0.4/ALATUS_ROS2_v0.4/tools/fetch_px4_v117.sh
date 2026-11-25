#!/usr/bin/env bash
set -euo pipefail
px4_target="${1:-$HOME/PX4-Autopilot-v1.17.0}"
if [[ -e "$px4_target" ]]; then echo 'Destination exists; refusing overwrite'; exit 2; fi
git clone --branch v1.17.0 --recursive https://github.com/PX4/PX4-Autopilot.git "$px4_target"
test "$(git -C "$px4_target" rev-parse HEAD)" = d6f12ad1c4f70ad3230afd7d86e971421e02fef4
git -C "$px4_target" submodule status --recursive > "$px4_target/alatus-submodules.txt"
printf '%s\n' 'Source fetched. Build and simulation NOT YET TESTED.'
