#!/usr/bin/env bash
set -euo pipefail
exec ros2 bag record -o "${1:?output-directory required}" \
 /alatus/detection_frame /alatus/track_estimate /alatus/aircraft_state \
 /alatus/visual_command /alatus/mission_state /alatus/safety_status /alatus/sitl_authority \
 /mavros/state /mavros/local_position/pose /mavros/local_position/velocity_local /mavros/vfr_hud /clock
