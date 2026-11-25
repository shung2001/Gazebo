# Build on the Pi itself, or with buildx --platform linux/arm64 and a working builder.
ARG ROS_BASE=ros:humble-ros-base-jammy
FROM ${ROS_BASE}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive CMAKE_BUILD_PARALLEL_LEVEL=2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake python3-dev python3-colcon-common-extensions python3-pytest python3-yaml git ca-certificates \
    ros-humble-launch-ros ros-humble-std-srvs ros-humble-rcl-interfaces ros-humble-ament-cmake \
    ros-humble-rosidl-default-generators ros-humble-rosidl-default-runtime ros-humble-std-msgs ros-humble-builtin-interfaces \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/alatus
COPY src/ src/
COPY tests/ tests/
COPY tools/ tools/
COPY design/ design/
COPY docs/ docs/
COPY deploy/ deploy/
# Optional messages only. Never silently use main/latest; empty means no PX4 dependency.
ARG PX4_MSGS_SHA=""
RUN if [[ -n "$PX4_MSGS_SHA" ]]; then \
      [[ "$PX4_MSGS_SHA" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2; \
      git init src/px4_msgs && git -C src/px4_msgs remote add origin https://github.com/PX4/px4_msgs.git && \
      git -C src/px4_msgs fetch --depth 1 origin "$PX4_MSGS_SHA" && \
      git -C src/px4_msgs checkout --detach FETCH_HEAD && \
      test "$(git -C src/px4_msgs rev-parse HEAD)" = "${PX4_MSGS_SHA,,}" && \
      printf '%s\n' "$PX4_MSGS_SHA" > /opt/alatus/px4_msgs-source-sha.txt; \
    fi
RUN source /opt/ros/humble/setup.bash && \
    colcon build --event-handlers console_direct+ && \
    source install/setup.bash && \
    python3 tools/run_local_tests.py && \
    colcon test --event-handlers console_direct+ && colcon test-result --verbose
RUN groupadd --gid 10001 alatus && useradd --uid 10001 --gid 10001 --create-home alatus && \
    mkdir -p /run/alatus /data && chown alatus:alatus /run/alatus /data
COPY deploy/entrypoint.sh /usr/local/bin/alatus-entrypoint
RUN chmod 0755 /usr/local/bin/alatus-entrypoint
ENV PYTHONUNBUFFERED=1 ROS_LOG_DIR=/data/ros-log
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/alatus-entrypoint"]
CMD ["ros2", "launch", "alatus_bringup", "onboard_observer.launch.py"]
