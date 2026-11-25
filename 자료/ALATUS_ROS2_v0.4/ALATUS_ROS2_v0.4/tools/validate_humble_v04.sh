#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
bash tools/test_v04.sh
colcon test --event-handlers console_direct+
colcon test-result --verbose
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
mkdir -p log/acceptance
ros2 launch alatus_bringup mock_shadow.launch.py > log/acceptance/v04-shadow.log 2>&1 &
launch_pid=$!
trap 'kill -INT "$launch_pid" 2>/dev/null || true; wait "$launch_pid" || true' EXIT
python3 tools/ros_v04_smoke.py
