> 이 파일은 v0.1/v0.2 설계 이력입니다. 현재 v0.3 실행·파라미터·PX4 SHA 설정은 IMPLEMENTED_PARAMETERS_V03_KO.md와 RPI_DOCKER_WALKTHROUGH_KO.md가 우선합니다.

# ROS 2 노드별 파라미터 상세 설계 v0.2

작성일: 2026-11-02. 런타임 소스 버전은 0.1.0 그대로입니다. 이번 v0.2는 상세 설계 문서 개정입니다.
이 파일은 승인된 기체 요구조건이 아니라 소스에 근거한 현재 계약과 후속 구현 설계입니다.

## 먼저 용어를 구분합니다

* ROS parameter: 특정 노드의 설정값. 예: /mock_perception의 dropout.
* topic message field: 매번 전송하는 데이터. 예: TargetDetection.confidence. 토픽 자체에 ROS parameter가 달리는 것은 아닙니다.
* launch argument: 실행 구성을 정하는 입력. 현재 shadow.launch.py는 use_sim_time 하나를 노드들에 전달합니다.
* source constant: 코드에 고정된 값. 현재 timeout 0.5, 확인 횟수 3, gain 0.5 등은 ROS parameter가 아닙니다.

ROS 2 파라미터는 노드별 값과 descriptor를 가지며 시작/실행 중 설정을 지원합니다.
[Humble 공식 개념 문서](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Basic/About-Parameters.rst)

## 표의 상태와 변경 규칙

* implemented: 소스에서 declare_parameter로 선언하고 사용하는 실제 설정.
* framework: rclpy의 use_sim_time. 프레임워크 기능이며 기체 안전감시가 아닙니다.
* proposed_not_implemented: 새로 설계한 이름. 현재 ros2 param set/YAML로 적용할 수 없습니다.

제안 범위는 초보자 desktop Mock 시험을 위한 설계 출발점입니다. 실제 공력·카메라·접근속도에서 산출한 수치가 아닙니다.
제안 파라미터는 기본적으로 시작 시 고정하도록 구현할 계획입니다. 변경 시 연결된 노드를 함께 재시작하고 시험을 반복합니다.
현재 px4_status의 설정은 초기화 때만 읽습니다. 실행 중 set이 성공해도 구독·버전 gate가 다시 구성되지는 않습니다.
이것을 런타임 변경 지원으로 오해하면 안 됩니다.

## 현재 고정 정책: 파라미터로 만들지 않을 항목

| 항목 | 정책 |
|---|---|
| 제어 송신 | 구현하지 않음. enable_control, arm_on_start 등의 스위치도 만들지 않음 |
| control_allowed | 항상 false. 운영자가 true로 바꾸는 파라미터가 아님 |
| shadow_only | 정상 생성 메시지에서 항상 true |
| ABORT 유지 | 표적/상태 회복만으로 자동 해제 금지; false 서비스 요청 후 재시작 |
| flight readiness / override unknown | unknown을 safe로 바꾸는 설정 금지 |
| topic 이름 | 기본 계약 유지; 실험 시 ROS remap 사용. 이름 변경은 producer/consumer 동시 검토 |
| 내부 QoS | reliable, volatile, keep_last 10; v0.1에서 parameter화하지 않음 |
| PX4 구독 QoS | sensor_data; 실제 endpoint와 호환성 확인 |

## 노드별 책임과 현재 동작

| 노드 | 입력 | 출력 | 초기/고장 동작 |
|---|---|---|---|
| mock_perception | ROS clock, dropout | detection | 10 Hz; dropout=true도 메시지는 계속 나가지만 valid=false |
| tracker | detection | target_track | 첫 detection 전 미발행; 관측 timestamp 유지; stale이면 valid=false |
| mock_status | ROS clock | aircraft_status | 10 Hz; source=MOCK_NOT_AIRCRAFT; readiness/override unknown |
| mission | track, status, SetBool 서비스 | mission_state | IDLE; 시작 후 조건에 따라 SEARCH/TRACK_SHADOW/ABORT |
| guidance | track, mission, status | guidance_proposal | invalid 기본; 허용 시 영상 오차만 계산 |
| safety_gate | proposal, mission, status | safety_status | 입력 누락/오래됨이면 inputs_valid=false; 제어는 항상 금지 |
| px4_status (선택) | PX4 VehicleStatus | aircraft_status | contract 불일치/px4_msgs 부재이면 시작 실패; 수신 중단 시 발행 중단 |


## mock_perception


### 현재 구현된 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| dropout | bool / `false` | - | true/false | runtime | true publishes invalid detections; does not stop publication | set true -> invalid track -> ABORT after TRACK_SHADOW |

### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /mock_perception use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| optical_frame_id | string / `"camera_optical"` | frame name | nonempty; same frame at producer/consumers | startup only / reject runtime changes once implemented | Image convention identifier only, not proof that TF/extrinsics exist | wrong frame -> invalid; no body-angle interpretation |
| center_x_norm | float64 / `0.5` | image width fraction | 0..1 | startup only / reject runtime changes once implemented | Sinusoid centre | centre-amplitude>=0; centre+amplitude<=1 |
| center_y_norm | float64 / `0.5` | image height fraction | 0..1 | startup only / reject runtime changes once implemented | Vertical centre | edge and out-of-range |
| amplitude_x_norm | float64 / `0.2` | image width fraction | 0..0.5 and centre±amplitude inside [0,1] | startup only / reject runtime changes once implemented | Horizontal sinusoid amplitude | coupled bound checks |
| angular_frequency_rad_s | float64 / `0.3` | rad/s | 0..10; test signal only | startup only / reject runtime changes once implemented | Time variation of mock pattern, not aircraft angular rate | zero frequency and periodicity |
| confidence | float64 / `0.95` | dimensionless | 0..1 finite | startup only / reject runtime changes once implemented | Mock detector confidence | low confidence -> invalid track |
| target_id | int64 / `1` | identifier | 0..4294967295 | startup only / reject runtime changes once implemented | Single mock target identity | identity change restarts confirmation |

## tracker


### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /tracker use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| detection_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop test envelope | startup only / reject runtime changes once implemented | Observation freshness, not publisher heartbeat; preserve source timestamp | boundary at max age; stale/future/clock rewind |
| min_confidence | float64 / `0.7` | dimensionless | 0..1, finite; identical baseline across consumers | startup only / reject runtime changes once implemented | Detector confidence threshold, not calibrated probability | just-below/at threshold; NaN; confidence>1 |
| optical_frame_id | string / `"camera_optical"` | frame name | nonempty; same frame at producer/consumers | startup only / reject runtime changes once implemented | Image convention identifier only, not proof that TF/extrinsics exist | wrong frame -> invalid; no body-angle interpretation |
| confirm_hits | int64 / `3` | observations | 1..100 | startup only / reject runtime changes once implemented | Consecutive increasing observations of same ID | N-1 invalid; N valid; duplicate does not count |
| max_observation_gap_s | float64 / `0.5` | s | 0.05..2.0; <= detection_max_age_s for baseline | startup only / reject runtime changes once implemented | Maximum source-time gap for consecutive hits | gap above limit restarts hit count |

## mock_status


### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /mock_status use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| status_received | bool / `true` | - | true/false | startup only / reject runtime changes once implemented | Fault injection: telemetry availability flag | fault -> documented mission behavior; no command output |
| failsafe | bool / `false` | - | true/false | startup only / reject runtime changes once implemented | Fault injection: failsafe status flag | fault -> documented mission behavior; no command output |
| armed | bool / `false` | - | true/false | startup only / reject runtime changes once implemented | Diagnostic flag only; no arming command | fault -> documented mission behavior; no command output |
| nav_state | int64 / `0` | - | 0..255; numeric labels depend on firmware | startup only / reject runtime changes once implemented | Diagnostic mode number only | fault -> documented mission behavior; no command output |

## mission


### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /mission use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| track_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop test envelope | startup only / reject runtime changes once implemented | Observation freshness, not publisher heartbeat; preserve source timestamp | boundary at max age; stale/future/clock rewind |
| status_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop envelope | startup only / reject runtime changes once implemented | Status receipt age; cannot detect upstream stale transport content | stop status publisher; ABORT and invalid diagnostics |
| min_confidence | float64 / `0.7` | dimensionless | 0..1, finite; identical baseline across consumers | startup only / reject runtime changes once implemented | Detector confidence threshold, not calibrated probability | just-below/at threshold; NaN; confidence>1 |
| optical_frame_id | string / `"camera_optical"` | frame name | nonempty; same frame at producer/consumers | startup only / reject runtime changes once implemented | Image convention identifier only, not proof that TF/extrinsics exist | wrong frame -> invalid; no body-angle interpretation |
| expected_status_source | string / `"MOCK_NOT_AIRCRAFT"` | - | MOCK_NOT_AIRCRAFT or PX4_VEHICLE_STATUS_ONLY; no wildcard | startup only / reject runtime changes once implemented | Prevent mock/real status mixing | wrong source -> ABORT when requested |

## guidance


### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /guidance use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| track_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop test envelope | startup only / reject runtime changes once implemented | Observation freshness, not publisher heartbeat; preserve source timestamp | boundary at max age; stale/future/clock rewind |
| status_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop envelope | startup only / reject runtime changes once implemented | Status receipt age; cannot detect upstream stale transport content | stop status publisher; ABORT and invalid diagnostics |
| mission_max_age_s | float64 / `0.5` | s | 0.05..2.0 | startup only / reject runtime changes once implemented | Reject stale mission permission | stop mission publisher; proposal/gate invalid |
| min_confidence | float64 / `0.7` | dimensionless | 0..1, finite; identical baseline across consumers | startup only / reject runtime changes once implemented | Detector confidence threshold, not calibrated probability | just-below/at threshold; NaN; confidence>1 |
| optical_frame_id | string / `"camera_optical"` | frame name | nonempty; same frame at producer/consumers | startup only / reject runtime changes once implemented | Image convention identifier only, not proof that TF/extrinsics exist | wrong frame -> invalid; no body-angle interpretation |
| expected_status_source | string / `"MOCK_NOT_AIRCRAFT"` | - | same as mission | startup only / reject runtime changes once implemented | Reject mixed sources | source mismatch -> valid=false |
| image_center_x | float64 / `0.5` | dimensionless | 0..1 finite | startup only / reject runtime changes once implemented | Horizontal diagnostic reference | formula, sign and clipping boundaries |
| image_center_y | float64 / `0.5` | dimensionless | 0..1 finite | startup only / reject runtime changes once implemented | Vertical diagnostic reference | formula, sign and clipping boundaries |
| diagnostic_gain | float64 / `0.5` | dimensionless | 0..2 finite; illustrative only | startup only / reject runtime changes once implemented | Dimensionless proportional diagnostic gain | formula, sign and clipping boundaries |
| correction_limit_norm | float64 / `0.2` | dimensionless | 0..0.2 finite for v0.1 gate | startup only / reject runtime changes once implemented | Diagnostic clipping limit; not a physical actuator limit | formula, sign and clipping boundaries |

## safety_gate


### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /safety_gate use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| publish_rate_hz | float64 / `10.0` | Hz | 1..50; engineering starting range, not aircraft requirement | startup only / reject runtime changes once implemented | Timer output frequency; tracker emits nothing until first detection in current code | measure with topic hz and receipt-time logs; stress at allowed limits |
| observation_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop test envelope | startup only / reject runtime changes once implemented | Observation freshness, not publisher heartbeat; preserve source timestamp | boundary at max age; stale/future/clock rewind |
| status_max_age_s | float64 / `0.5` | s | 0.05..2.0; provisional desktop envelope | startup only / reject runtime changes once implemented | Status receipt age; cannot detect upstream stale transport content | stop status publisher; ABORT and invalid diagnostics |
| mission_max_age_s | float64 / `0.5` | s | 0.05..2.0 | startup only / reject runtime changes once implemented | Reject stale mission permission | stop mission publisher; proposal/gate invalid |
| optical_frame_id | string / `"camera_optical"` | frame name | nonempty; same frame at producer/consumers | startup only / reject runtime changes once implemented | Image convention identifier only, not proof that TF/extrinsics exist | wrong frame -> invalid; no body-angle interpretation |
| expected_status_source | string / `"MOCK_NOT_AIRCRAFT"` | - | same as mission | startup only / reject runtime changes once implemented | Reject mixed sources | source mismatch -> inputs_valid=false |
| proposal_max_age_s | float64 / `0.5` | s | 0.05..2.0 | startup only / reject runtime changes once implemented | Proposal generation-time freshness | new proposal with stale observation is still invalid |
| correction_limit_norm | float64 / `0.2` | dimensionless | 0..0.2; must match guidance | startup only / reject runtime changes once implemented | Independent diagnostic range check | above limit; float32 round-trip tolerance; NaN/Inf |

## px4_status


### 현재 구현된 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| firmware_tag | string / `""` | - | exact v1.16.0 | startup consumed; restart required (not read_only enforced) | User-declared firmware tag, not automatic discovery | missing/incorrect contract -> startup failure; inspect actual telemetry separately |
| px4_msgs_ref | string / `""` | - | exact release/1.16 | startup consumed; restart required (not read_only enforced) | User-declared reference; record actual SHA separately | missing/incorrect contract -> startup failure; inspect actual telemetry separately |
| contract_reviewed | bool / `false` | - | true is required to start | startup consumed; restart required (not read_only enforced) | Explicit review acknowledgement; not cryptographic verification | missing/incorrect contract -> startup failure; inspect actual telemetry separately |
| status_topic | string / `"/fmu/out/vehicle_status_v1"` | - | nonempty discovered VehicleStatus topic | startup consumed; restart required (not read_only enforced) | PX4 subscription topic; actual runtime name/type/QoS must be checked | missing/incorrect contract -> startup failure; inspect actual telemetry separately |

### 프레임워크 설정

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| use_sim_time | bool / `false` | - | true/false; connected nodes must use one clock domain | Framework permits change; project policy: restart the complete pipeline | ROS clock source. false=system time, true=/clock; not a monotonic watchdog | ros2 param get /px4_status use_sim_time; check /clock when true |

### 후속 구현 설계 — 현재 적용 불가

| 이름 | 타입 / 기본값 | 단위 | 허용 조건 | 변경 시점 | 목적 | 확인 시험 |
|---|---|---|---|---|---|---|
| expected_message_version | int64 / `1` | version | exact 1 for current reviewed contract | startup only / reject runtime changes once implemented | Exposed constant does not permit other contracts | version mismatch rejects startup |
| firmware_commit_sha | string / `""` | git SHA | required reviewed commit for PX4 profile | startup only / reject runtime changes once implemented | Provenance record, not runtime firmware verification | record against actual build artifact |
| px4_msgs_commit_sha | string / `""` | git SHA | required reviewed commit for PX4 profile | startup only / reject runtime changes once implemented | Provenance record, not automatic wire-schema validation | compare built source manifest |

## 여러 노드 사이의 제약

1. producer/consumer의 optical_frame_id와 clock domain을 동일하게 유지합니다.
2. tracker의 confidence 기준을 낮추더라도 mission/guidance의 별도 0.7 검사는 현재 그대로입니다. 한 곳만 변경하면 예상과 다르게 거절됩니다.
3. guidance의 correction_limit_norm과 safety의 허용 한계를 일치시킵니다. gate의 현재 허용치는 float32 오차를 고려한 0.200001입니다.
4. 제안하는 기본 10 Hz에서 0.5초 age는 약 5주기입니다. 실제 지연 분포를 측정하기 전 timeout을 늘려 오류를 숨기지 않습니다.
5. 3회 확인은 10 Hz에서 첫 관측 후 대략 0.2초를 더 요구합니다. callback 지연과 timer 위상 때문에 정확한 지연 보장은 아닙니다.
6. publish rate 범위와 timeout 조합을 모두 허용하는 것은 아닙니다. 적어도 T_age > T_publish + T_pipeline_budget 조건을 확인합니다.
7. 타임스탬프의 age와 monotonic 수신 간격은 다른 지표입니다. 향후 둘 다 확인하고, clock pause/rewind는 별도 고장으로 기록합니다.
8. source 문자열 검사는 제안만 되어 있으며 현재 코드에는 없습니다. 현재 혼합 publisher 방지는 실행 구성과 topic info 확인에 의존합니다.

## 파라미터 구현 설계

* 타입/기본값을 먼저 선언하고 ParameterDescriptor에 description과 read_only, 수치 range를 지정합니다.
* float는 isfinite를 추가 검사합니다. NaN/Inf를 수치 range만으로 검출한다고 가정하지 않습니다.
* 최소/최대·gain/limit·centre/amplitude 같은 결합 조건은 전체 후보 설정으로 검증합니다.
* startup-only 값은 read_only로 구현합니다. 잘못된 YAML/override는 시작 시 명확한 오류로 실패시킵니다.
* 런타임 변경을 지원하는 값만 callback을 추가하고, 거절된 후보가 객체 상태를 바꾸지 않게 합니다.
* 여러 값을 함께 바꿔야 한다면 set_parameters_atomically를 사용하도록 API를 설계합니다. 단순 set_parameters는 전체가 한 번에 적용된다고 보장하지 않습니다.
* Humble rclpy API에 실제로 있는 callback만 사용합니다. 다른 배포판의 pre/post callback을 그대로 복사하지 않습니다.
[Humble rclpy 구현](https://raw.githubusercontent.com/ros2/rclpy/humble/rclpy/rclpy/node.py)

## 후속 인식 연결 노드 설계 — 미구현

실제 detector 전용 API는 선택된 detector/메시지를 받은 후 고정합니다. 특정 YOLO ROS 패키지를 이미 지원한다고 주장하지 않습니다.

| 후보 노드/파라미터 | 타입/초깃값 | 설계 조건 |
|---|---|---|
| detection_bridge.input_topic | string / 미정 | 실제 detector output topic/type를 확인한 뒤 고정 |
| detection_bridge.input_message_type | 설계 기록 / 미정 | Python 구독 타입은 adapter 코드에서 결정; 임의 문자열만으로 변환 가능하지 않음 |
| detection_bridge.target_class_id | string 또는 int / 미정 | detector class map과 팀 표적 정의 필요 |
| detection_bridge.min_confidence | float64 / 0.7 후보 | detector confidence 의미를 확인; calibrated probability라고 부르지 않음 |
| detection_bridge.camera_optical_frame | string / camera_optical 후보 | 실제 카메라 frame과 일치시킨 뒤 producer/consumer 함께 변경 |
| detection_bridge.max_input_age_s | float64 / 0.5 후보 | sensor exposure stamp 기준, detector 처리 지연 포함 |
| detection_bridge.selection_policy | string / 미정 | 다중 표적 시 stable ID·우선순위·동점 정책을 명시; confidence만으로 ID 유지 불가 |
| detection_bridge.image_width/height | 입력 metadata 사용 | 실제 프레임 크기와 일치; 임의 640×480 고정 금지 |

현재 TargetDetection에는 bbox·클래스·source sequence·카메라 ID가 없습니다. 필요한 경우 v2 메시지를 새 타입/토픽으로 설계합니다.
기존 타입의 필드를 조용히 바꾸어 서로 다른 빌드가 같은 topic에서 통신하도록 하지 않습니다.
