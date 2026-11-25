#!/usr/bin/env bash
set -euo pipefail
px4_target="${PX4_V117_DIR:-$HOME/PX4-Autopilot-v1.17.0}"
test "$(git -C "$px4_target" rev-parse HEAD)" = d6f12ad1c4f70ad3230afd7d86e971421e02fef4
cd "$px4_target"
if [[ "${1:-baseline}" == vision ]]; then
  test -f Tools/simulation/gz/models/advanced_plane_vision/model.sdf
  test -x build/px4_sitl_default/bin/px4
  export PX4_SYS_AUTOSTART=4008 PX4_SIM_MODEL=gz_advanced_plane_vision PX4_GZ_WORLD=alatus_recovery
  exec build/px4_sitl_default/bin/px4
else
  exec make px4_sitl gz_advanced_plane
fi
