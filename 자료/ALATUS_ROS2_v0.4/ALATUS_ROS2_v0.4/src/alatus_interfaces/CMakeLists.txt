cmake_minimum_required(VERSION 3.8)
project(alatus_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/TargetDetection.msg"
  "msg/TargetTrack.msg"
  "msg/AircraftStatus.msg"
  "msg/MissionState.msg"
  "msg/GuidanceProposal.msg"
  "msg/SafetyStatus.msg"
  "msg/PixelDetection.msg"
  "msg/DetectionFrame.msg"
  "msg/TrackEstimate.msg"
  "msg/AircraftState.msg"
  "msg/VisualCommand.msg"
  DEPENDENCIES std_msgs builtin_interfaces)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
