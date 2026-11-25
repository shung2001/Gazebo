# 구현된 노드 파라미터 v0.3

현재 실행 기준입니다. dropout만 runtime 변경, 나머지 application 설정은 read_only입니다.
use_sim_time은 rclpy 설정이며 실행 중 변경을 거절합니다. onboard launch는 false입니다.
PX4는 고정 v1.16 gate 대신 검토한 compatibility profile과 설치된 msg hash/type/version을 검사합니다.
아래 범위는 관찰 시스템 개발값이며 비행 허용조건이 아닙니다. 결합 검사는 parameters.py를 함께 확인합니다.

## mock_perception

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| dropout | bool | `false` | validator 참조 | runtime | true publishes invalid detections; does not stop publication |
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Image convention identifier only, not proof that TF/extrinsics exist |
| center_x_norm | float64 | `0.5` | [0.0, 1.0] | startup/read_only | Sinusoid centre |
| center_y_norm | float64 | `0.5` | [0.0, 1.0] | startup/read_only | Vertical centre |
| amplitude_x_norm | float64 | `0.2` | [0.0, 0.5] | startup/read_only | Horizontal sinusoid amplitude |
| angular_frequency_rad_s | float64 | `0.3` | [0.0, 10.0] | startup/read_only | Time variation of mock pattern, not aircraft angular rate |
| confidence | float64 | `0.95` | [0.0, 1.0] | startup/read_only | Mock detector confidence |
| target_id | int64 | `1` | [0, 4294967295] | startup/read_only | Single mock target identity |

## px4_status

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| firmware_tag | string | `""` | validator 참조 | startup/read_only | User-declared firmware tag, not automatic discovery |
| px4_msgs_ref | string | `""` | validator 참조 | startup/read_only | User-declared reference; record actual SHA separately |
| contract_reviewed | bool | `false` | validator 참조 | startup/read_only | Explicit review acknowledgement; not cryptographic verification |
| status_topic | string | `"/fmu/out/vehicle_status_v1"` | validator 참조 | startup/read_only | PX4 subscription topic; actual runtime name/type/QoS must be checked |
| expected_message_version | int64 | `1` | [0, 65535] | startup/read_only | Exposed constant does not permit other contracts |
| firmware_commit_sha | string | `""` | validator 참조 | startup/read_only | Provenance record, not runtime firmware verification |
| px4_msgs_commit_sha | string | `""` | validator 참조 | startup/read_only | Provenance record, not automatic wire-schema validation |
| contract_profile_path | string | `""` | validator 참조 | startup/read_only | Reviewed compatibility JSON profile path; required to start PX4 adapter |

## tracker

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| detection_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Observation freshness, not publisher heartbeat; preserve source timestamp |
| min_confidence | float64 | `0.7` | [0.0, 1.0] | startup/read_only | Detector confidence threshold, not calibrated probability |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Image convention identifier only, not proof that TF/extrinsics exist |
| confirm_hits | int64 | `3` | [1, 100] | startup/read_only | Consecutive increasing observations of same ID |
| max_observation_gap_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Maximum source-time gap for consecutive hits |

## mock_status

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| status_received | bool | `true` | validator 참조 | startup/read_only | Fault injection: telemetry availability flag |
| failsafe | bool | `false` | validator 참조 | startup/read_only | Fault injection: failsafe status flag |
| armed | bool | `false` | validator 참조 | startup/read_only | Diagnostic flag only; no arming command |
| nav_state | int64 | `0` | [0, 255] | startup/read_only | Diagnostic mode number only |

## mission

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| track_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Observation freshness, not publisher heartbeat; preserve source timestamp |
| status_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Status receipt age; cannot detect upstream stale transport content |
| min_confidence | float64 | `0.7` | [0.0, 1.0] | startup/read_only | Detector confidence threshold, not calibrated probability |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Image convention identifier only, not proof that TF/extrinsics exist |
| expected_status_source | string | `"MOCK_NOT_AIRCRAFT"` | validator 참조 | startup/read_only | Prevent mock/real status mixing |

## guidance

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| track_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Observation freshness, not publisher heartbeat; preserve source timestamp |
| status_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Status receipt age; cannot detect upstream stale transport content |
| mission_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Reject stale mission permission |
| min_confidence | float64 | `0.7` | [0.0, 1.0] | startup/read_only | Detector confidence threshold, not calibrated probability |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Image convention identifier only, not proof that TF/extrinsics exist |
| expected_status_source | string | `"MOCK_NOT_AIRCRAFT"` | validator 참조 | startup/read_only | Reject mixed sources |
| image_center_x | float64 | `0.5` | [0.0, 1.0] | startup/read_only | Horizontal diagnostic reference |
| image_center_y | float64 | `0.5` | [0.0, 1.0] | startup/read_only | Vertical diagnostic reference |
| diagnostic_gain | float64 | `0.5` | [0.0, 2.0] | startup/read_only | Dimensionless proportional diagnostic gain |
| correction_limit_norm | float64 | `0.2` | [0.0, 0.2] | startup/read_only | Diagnostic clipping limit; not a physical actuator limit |

## safety_gate

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| publish_rate_hz | float64 | `10.0` | [1.0, 50.0] | startup/read_only | Timer output frequency; tracker emits nothing until first detection in current code |
| observation_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Observation freshness, not publisher heartbeat; preserve source timestamp |
| status_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Status receipt age; cannot detect upstream stale transport content |
| mission_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Reject stale mission permission |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Image convention identifier only, not proof that TF/extrinsics exist |
| expected_status_source | string | `"MOCK_NOT_AIRCRAFT"` | validator 참조 | startup/read_only | Reject mixed sources |
| proposal_max_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Proposal generation-time freshness |
| correction_limit_norm | float64 | `0.2` | [0.0, 0.2] | startup/read_only | Independent diagnostic range check |

## perception_socket

| 이름 | 타입 | 기본값 | 범위 | 변경 | 의미 |
|---|---|---|---|---|---|
| socket_path | string | `"/run/alatus/perception.sock"` | validator 참조 | startup/read_only | Unix datagram input path; Linux only |
| optical_frame_id | string | `"camera_optical"` | validator 참조 | startup/read_only | Expected camera frame |
| target_class_id | string | `"target"` | validator 참조 | startup/read_only | Exact detector class label; must be configured to the actual model |
| min_confidence | float64 | `0.7` | [0.0, 1.0] | startup/read_only | Minimum detector confidence |
| max_input_age_s | float64 | `0.5` | [0.05, 2.0] | startup/read_only | Exposure timestamp age in shared host system clock |
| publish_rate_hz | float64 | `50.0` | [1.0, 100.0] | startup/read_only | Maximum socket polling frequency; not inference rate |
| max_datagrams_per_tick | int64 | `16` | [1, 128] | startup/read_only | Bounded input work per timer callback |

## 공통 검증

* float는 유한수만 허용하고 bool/int/float/string을 구분합니다.
* centre±amplitude는 [0,1], tracker gap<=detection age, input age>timer period입니다.
* expected_status_source는 MOCK_NOT_AIRCRAFT 또는 PX4_VEHICLE_STATUS_ONLY만 허용합니다.
* status_topic은 /fmu/out/ 하위 telemetry만, profile의 message version suffix와 일치해야 합니다.
* PX4 profile은 실제 firmware/msg SHA·MSG SHA256·필드·enum 검토가 끝나기 전 reviewed=false입니다.
* profile 선언은 실제 firmware를 자동 검증하는 attestation이나 통합 성공 증거가 아닙니다.
