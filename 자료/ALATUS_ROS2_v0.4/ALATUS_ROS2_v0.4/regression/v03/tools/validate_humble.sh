#!/usr/bin/env bash
# Execute from workspace root inside a prepared Ubuntu 22.04/Humble environment.
set -eo pipefail
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
python3 tools/run_local_tests.py
colcon test --event-handlers console_direct+
colcon test-result --verbose
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
mkdir -p log/acceptance
ros2 launch alatus_bringup shadow.launch.py > log/acceptance/shadow.log 2>&1 &
launch_pid=$!
cleanup() {
  kill -TERM "$launch_pid" 2>/dev/null || true
  wait "$launch_pid" 2>/dev/null || true
}
trap cleanup EXIT
python3 tools/ros_parameter_smoke.py
python3 tools/ros_smoke.py
