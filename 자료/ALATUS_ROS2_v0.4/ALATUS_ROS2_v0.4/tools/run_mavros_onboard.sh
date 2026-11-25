#!/usr/bin/env bash
set -eo pipefail
: "${ALATUS_FCU_URL:?Set confirmed serial device and baud, e.g. a verified /dev/serial/by-id path:baud}"
source /opt/ros/humble/setup.bash
mavros_share="$(ros2 pkg prefix --share mavros)"
exec ros2 run mavros mavros_node --ros-args \
 --params-file "$mavros_share/launch/px4_pluginlists.yaml" \
 --params-file "$mavros_share/launch/px4_config.yaml" \
 -p "fcu_url:=$ALATUS_FCU_URL" -p gcs_url:='' -p use_sim_time:=false
