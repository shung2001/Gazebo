#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
mavros_share="$(ros2 pkg prefix --share mavros)"
exec ros2 run mavros mavros_node --ros-args \
 --params-file "$mavros_share/launch/px4_pluginlists.yaml" \
 --params-file "$mavros_share/launch/px4_config.yaml" \
 -p fcu_url:='udp://:14540@127.0.0.1:14557' -p gcs_url:='' \
 -p tgt_system:=1 -p tgt_component:=1 -p use_sim_time:=true
