#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
exec ros2 run ros_gz_bridge parameter_bridge \
 '/alatus/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
 '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' \
 --ros-args -p use_sim_time:=true
