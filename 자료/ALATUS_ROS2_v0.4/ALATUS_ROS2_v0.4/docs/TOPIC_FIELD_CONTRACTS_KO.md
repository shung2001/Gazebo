# v0.4 Topic / Field Contract

모든 ROS pub/sub는 단일 source를 원칙으로 한다. Detection/Track/Command header와 observation_stamp를 구분한다. 모든 추가 필드 정의는 아래 실제 .msg에서 생성했다.

| Topic | Type | Publisher | Subscriber | QoS | Time/Frame |
|---|---|---|---|---|---|
| /alatus/detection_frame | DetectionFrame | vision_perception | vision_pipeline | reliable keep-last 10 | exposure/replay timestamp, camera_optical |
| /alatus/detection | TargetDetection (legacy) | vision_perception | optional legacy observer | reliable 10 | exposure time, normalized center; ambiguous invalid |
| /alatus/track_estimate | TrackEstimate | vision_pipeline | sitl_sender/logger | reliable 10 | header current estimate time, observation_stamp last accepted measurement |
| /alatus/target_track | TargetTrack (legacy) | vision_pipeline | optional observer | reliable 10 | header LAST observation time, not timer time |
| /alatus/aircraft_state | AircraftState | state_adapter OR explicit Mock | pipeline/sender | reliable 10 (MAVROS input best-effort compatible) | ENU map, FLU body; per-field validity/ages |
| /alatus/aircraft_status | AircraftStatus (legacy) | same selected state producer | optional legacy observer | reliable 10 | snapshot; unknown readiness/manual not asserted |
| /alatus/mission_state | MissionState | vision_pipeline | sender/logger | reliable 10 | current ROS time |
| /alatus/visual_command | VisualCommand | vision_pipeline | separate SITL sender | reliable 10 | header computation time, observation_stamp original time, ENU map |
| /alatus/guidance_proposal | GuidanceProposal (legacy) | vision_pipeline | observer | reliable 10 | dimensionless diagnostic, never a PX4 command |
| /alatus/safety_status | SafetyStatus | vision_pipeline | observer | reliable 10 | control_allowed always false |
| /alatus/sitl_authority | SafetyStatus | separate sender only | logger | reliable 10 | independent runtime stream permission |
| /mavros/setpoint_raw/local | mavros_msgs/PositionTarget | separate sender only | MAVROS | sensor best-effort, keep-last | ENU positions into MAVROS; NED enum; MAVROS converts |

Legacy TargetDetection.target_id=0 is a compatibility observation; KF track_id is authoritative in v0.4. Legacy TargetTrack.confidence retains the last accepted detector confidence and is not a posterior probability. Legacy GuidanceProposal.correction_norm remains zero rather than mislabelling physical course rate as normalized correction.

Timer may publish invalid snapshots at 20 Hz. Republishing never refreshes observation_stamp. System-time socket requires same-host exposure timestamp mapping; simulation uses /clock. Clock rewind/freeze latches fault; steady receipt watchdog also expires input. DDS adapter is not launched or built by default.

## AircraftState.msg

```text
# Snapshot stamp; per-field stamp+receipt freshness checked by adapter.
std_msgs/Header header
bool connected
bool armed
string mode
bool position_valid
bool attitude_valid
bool velocity_valid
bool angular_velocity_valid
bool airspeed_valid
bool gps_valid
bool battery_valid
bool failsafe_known
bool failsafe
bool manual_override_known
bool manual_override_active
# ENU metres, FLU body quaternion to ENU (xyzw), ENU m/s, FLU rad/s.
float64[3] position_enu_m
float64[4] attitude_xyzw
float64[3] velocity_enu_m_s
float64[3] angular_velocity_flu_rad_s
float64 airspeed_m_s
float64 altitude_local_enu_m
float64 battery_fraction
int32 gps_status
uint8 system_status
# ROS age seconds: State, Pose, Velocity, IMU, VFR, GPS, Battery; -1 means unavailable.
float64[7] field_age_s
string source
```

## AircraftStatus.msg

```text
# Header is ROS receipt time. px4_timestamp_us preserves the received PX4 timestamp.
# DDS may apply time offset; inspect the actual sync/clock configuration before interpreting it.
std_msgs/Header header
uint64 px4_timestamp_us
bool status_received
bool armed
bool failsafe
uint8 nav_state
bool flight_ready_known
bool flight_ready
bool manual_override_known
bool manual_override_active
string source
```

## DetectionFrame.msg

```text
# Exposure/input timestamp, not inference completion time. Optical frame.
std_msgs/Header header
uint64 sequence
string source
uint32 image_width
uint32 image_height
float64 inference_latency_s
PixelDetection[] detections
```

## GuidanceProposal.msg

```text
# Dimensionless image-space diagnostic. NOT heading, attitude or PX4 setpoint.
std_msgs/Header header
builtin_interfaces/Time observation_stamp
bool valid
bool shadow_only
float32 image_error_x
float32 image_error_y
float32 correction_norm
string reason
```

## MissionState.msg

```text
std_msgs/Header header
string state
bool proposal_allowed
string reason
```

## PixelDetection.msg

```text
int32 class_id
float32 confidence
float64[4] bbox_xyxy_px
```

## SafetyStatus.msg

```text
std_msgs/Header header
bool inputs_valid
bool control_allowed
string reason
```

## TargetDetection.msg

```text
std_msgs/Header header
bool valid
float32 confidence
float32 center_x_norm
float32 center_y_norm
uint32 target_id
```

## TargetTrack.msg

```text
# Header retains source observation time, never refresh stale observations.
std_msgs/Header header
bool valid
float32 confidence
float32 center_x_norm
float32 center_y_norm
uint32 track_id
uint32 consecutive_hits
```

## TrackEstimate.msg

```text
std_msgs/Header header
builtin_interfaces/Time observation_stamp
bool valid
uint32 track_id
uint32 image_width
uint32 image_height
float64[4] state_px
float64[16] covariance
float64 prediction_age_s
string state
string source
```

## VisualCommand.msg

```text
# Advisory only. Sender has an independent SITL permit and watchdog.
std_msgs/Header header
builtin_interfaces/Time observation_stamp
bool valid
bool shadow_only
string mode
float64 bearing_error_rad
float64 elevation_rad
float64 course_rate_rad_s
float64 bank_diagnostic_rad
float64 flight_path_angle_rad
float64[3] position_enu_m
bool saturated
string reason
```
