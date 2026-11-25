FROM ros:humble-ros-base-jammy
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
 build-essential python3-colcon-common-extensions python3-pytest python3-numpy python3-yaml \
 ros-humble-mavros ros-humble-mavros-extras ros-humble-cv-bridge ros-humble-launch-ros \
 ros-humble-std-srvs ros-humble-rosidl-default-generators && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/alatus
COPY src/ src/
COPY config/ config/
COPY tools/ tools/
COPY tests/ tests/
COPY regression/ regression/
RUN source /opt/ros/humble/setup.bash && colcon build && bash tools/test_v04.sh
RUN groupadd --gid 10001 alatus && useradd --uid 10001 --gid 10001 --create-home alatus && \
 mkdir -p /run/alatus /data && chown alatus:alatus /run/alatus /data
COPY deploy/entrypoint.sh /usr/local/bin/alatus-entrypoint
RUN chmod +x /usr/local/bin/alatus-entrypoint
USER 10001:10001
ENV ROS_LOG_DIR=/data/ros-log PYTHONUNBUFFERED=1
ENTRYPOINT ["/usr/local/bin/alatus-entrypoint"]
CMD ["ros2","launch","alatus_bringup","onboard_shadow.launch.py"]
