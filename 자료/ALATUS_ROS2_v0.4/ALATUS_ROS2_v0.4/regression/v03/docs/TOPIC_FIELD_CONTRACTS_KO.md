> 이 파일은 v0.1/v0.2 설계 이력입니다. 현재 v0.3 실행·파라미터·PX4 SHA 설정은 IMPLEMENTED_PARAMETERS_V03_KO.md와 RPI_DOCKER_WALKTHROUGH_KO.md가 우선합니다.

# 토픽·메시지·서비스 상세 계약 v0.2

여기의 필드는 실제 .msg에서 읽은 v0.1 계약입니다. ROS parameter와 구분합니다.
유효성 규칙 중 소비자가 현재 검사하는 내용과 운영/설계 규칙을 구분해서 읽으십시오.
메시지의 default는 생성 직후 값이며 invalid를 먼저 해석해야 합니다. 0이라는 수치가 센서 측정을 뜻하지 않습니다.

## 공통 통신 정책

내부 6개 topic: reliable / volatile / keep_last / depth10. publisher는 topic별 하나만 실행합니다.
ROS 제공 parameter_events 및 parameter service는 여기에 나열한 ALATUS application topic과 별개입니다.
QoS deadline/lifespan을 별도로 설정하지 않았고 timer 주기도 실시간 보장은 아닙니다.
모든 consumer는 같은 clock domain이어야 합니다. wall clock과 simulation clock을 섞지 않습니다.
순서는 header timestamp로 검사하되 source sequence가 없어 모든 중복/transport replay를 구분할 수는 없습니다.


## /alatus/detection

Type: `alatus_interfaces/msg/TargetDetection`. Publisher: mock_perception 또는 후속 detection_bridge. Subscriber: tracker. 주기: 10 Hz mock.

고장 정책: 관측 중단은 별도 timeout; valid=false도 계속 전송 가능.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | 관측 시각 + camera_optical | 센서 노출 시각의 공통 ROS clock; mock은 생성 시각 | 최신 수신 시각으로 원 관측을 덮어쓰지 않음 |
| valid | bool | 관측 존재 여부 | true라도 confidence/좌표/시간 별도 검사 | false이면 좌표를 유효한 표적으로 사용하지 않음 |
| confidence | float32 | 무차원 [0,1] | 유한수; v0.1 수신 기준 >=0.7 | 낮음/NaN/Inf/>1이면 invalid |
| center_x_norm | float32 | 영상 너비 정규화 [0,1] | x=u/W; 좌측0→우측1; W>0 | NaN/범위 밖은 invalid; 선회각 아님 |
| center_y_norm | float32 | 영상 높이 정규화 [0,1] | y=v/H; 상단0→하단1; H>0 | NaN/범위 밖은 invalid |
| target_id | uint32 | uint32 식별자 | 동일 물체의 연속성; 0도 허용 | ID 변경 시 확인 횟수 재시작; 추적기가 자동 연관하지 않음 |


## /alatus/target_track

Type: `alatus_interfaces/msg/TargetTrack`. Publisher: tracker. Subscriber: mission, guidance. 주기: 10 Hz; 첫 관측 후.

고장 정책: 유효 관측이 없으면 invalid; 원 stamp 보존.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | 원 관측 시각 + camera_optical | TargetDetection.header를 그대로 보존 | timer 재발행으로 stamp 갱신 금지 |
| valid | bool | 추적 확인 여부 | 동일 ID, 정상 시간·좌표·confidence의 3회 확인 | false 또는 observation age>0.5초이면 사용 금지 |
| confidence | float32 | 무차원 [0,1] | 마지막 detection 복사, 평균/필터 아님 | consumer도 >=0.7 재검사 |
| center_x_norm | float32 | 영상 너비 정규화 [0,1] | 마지막 detection의 값, 예측값 아님 | valid=false이면 조종 입력으로 사용 금지 |
| center_y_norm | float32 | 영상 높이 정규화 [0,1] | 마지막 detection의 값 | 좌표계 변환/3D 위치 아님 |
| track_id | uint32 | uint32 식별자 | detection.target_id 복사 | 자동 생성 global ID가 아님 |
| consecutive_hits | uint32 | 정상 관측 개수 | tracker의 누적 확인 횟수 | 현재 stale timer에서 logic.hits만 reset되어 메시지 카운트가 남을 수 있음; valid 우선 |


## /alatus/aircraft_status

Type: `alatus_interfaces/msg/AircraftStatus`. Publisher: mock_status 또는 px4_status 중 하나. Subscriber: mission, guidance, safety_gate. 주기: mock10 Hz / PX4 callback.

고장 정책: publisher 혼합 금지; status_ok=최근+received+not failsafe.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | ROS 수신/생성 시각; frame 빈 문자열 | mock 생성 또는 adapter 수신 시각 | upstream transport 지연은 이 stamp로 검출 불가 |
| px4_timestamp_us | uint64 | 수신 PX4 timestamp, microseconds | VehicleStatus.timestamp 그대로 복사; mock=0; DDS time offset 적용 가능 | clock/sync 설정 확인 전 boot/epoch 단정 또는 직접 차분 금지 |
| status_received | bool | 메시지 수신 여부 | mock=true; adapter callback=true | 비행 가능/추정기 정상 의미 아님 |
| armed | bool | arming 상태 | adapter는 ARMING_STATE_ARMED 상수로 비교; mock=false | false도 shadow 분석 가능; true여도 비행 허가 아님 |
| failsafe | bool | PX4 failsafe 상태 | mock=false; adapter에서 raw bool 복사 | true이면 status_ok=false |
| nav_state | uint8 | uint8 mode 번호 | mock=0; PX4 값 복사 | 숫자 의미는 선택 펌웨어 정의로 해석; manual override 판단 금지 |
| flight_ready_known | bool | 비행 준비 상태를 알고 있는가 | 현재 항상 false | unknown을 flight_ready=false와 의미상 구별 |
| flight_ready | bool | 알려진 경우의 준비 상태 | 현재 기본 false; known=false라 해석 불가 | 비행 readiness 센서/정책 미구현 |
| manual_override_known | bool | 수동개입 판정 가능 여부 | 현재 항상 false | nav_state만으로 true로 만들지 않음 |
| manual_override_active | bool | 알려진 경우의 수동개입 상태 | 현재 기본 false; known=false | 현재 gate는 이 필드를 검사하지 않음 |
| source | string | 출처 문자열 | MOCK_NOT_AIRCRAFT 또는 PX4_VEHICLE_STATUS_ONLY | 현재 consumer는 source 값 비교 미구현; 실행 시 publisher 단일성 확보 |


## /alatus/mission_state

Type: `alatus_interfaces/msg/MissionState`. Publisher: mission. Subscriber: guidance, safety_gate. 주기: 10 Hz.

고장 정책: 무응답 시 consumer freshness 만료.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | 판단 시각; frame 빈 문자열 | 10 Hz timer의 ROS clock | consumer는 0.5초 freshness 확인 |
| state | string | 문자열 상태 | IDLE/SEARCH/TRACK_SHADOW/ABORT | PX4 flight mode와 별개; 다른 문자열은 허용 상태로 취급 금지 |
| proposal_allowed | bool | shadow 계산 허용 | state==TRACK_SHADOW일 때만 true | 기체 제어 허가 아님 |
| reason | string | 사람용 설명 | 현재 공통 설명 문자열 | 기계적 고장 코드 아님; 문자열 파싱으로 제어하지 않음 |


## /alatus/guidance_proposal

Type: `alatus_interfaces/msg/GuidanceProposal`. Publisher: guidance. Subscriber: safety_gate. 주기: 10 Hz.

고장 정책: invalid값도 발행; observation freshness 별도.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | 계산 시각 + camera_optical | 주기마다 갱신 | 이 시각만 최신이어도 observation은 stale일 수 있음 |
| observation_stamp | builtin_interfaces/Time | 원 track 관측 시각 | TargetTrack.header.stamp 복사 | gate에서 별도로 0.5초 age 확인; 무관측 시 default0 |
| valid | bool | 영상 진단 계산 유효 | track+mission+status 정상일 때 true | false이면 수치가 0이어도 목표 달성 의미 아님 |
| shadow_only | bool | 분석 전용 표시 | 정상 노드에서 항상 true | false 입력이면 gate.inputs_valid=false |
| image_error_x | float32 | 무차원 [-0.5,0.5] | x-0.5; 오른쪽 표적 양수 | heading/yaw/roll rad가 아님 |
| image_error_y | float32 | 무차원 [-0.5,0.5] | y-0.5; 아래 표적 양수 | 고도/강하율 아님 |
| correction_norm | float32 | 무차원 [-0.2,0.2] | clip(-0.5*image_error_x) | gate는 유한수와 abs<=0.200001 확인; actuator 아님 |
| reason | string | 사람용 설명 | 현재 영상 진단 전용 설명 | 세부 invalid 원인코드 미구현 |


## /alatus/safety_status

Type: `alatus_interfaces/msg/SafetyStatus`. Publisher: safety_gate. Subscriber: 관찰자/rosbag. 주기: 10 Hz.

고장 정책: 수신이 끊기면 외부 관찰자가 검출해야 함.

| 필드 | 실제 ROS 타입 | 단위/의미 | 정상 계약 | 무효/주의 사항 |
|---|---|---|---|---|
| header | std_msgs/Header | 검사 시각; frame 빈 문자열 | 10 Hz timer | 현재 Mission으로 피드백되지 않음; 관찰·기록용 |
| inputs_valid | bool | shadow 입력 검사 통과 | proposal+observation+mission+status, frame/유한수/범위 검사 | flight_ready 검사나 공력 envelope 검증 아님 |
| control_allowed | bool | 항공기 제어 허가 | 현재 항상 false | 이를 true로 설정하는 파라미터/서비스 없음 |
| reason | string | 사람용 결과 문자열 | 정상 shadow 또는 INVALID_OR_STALE_INPUTS | 원인별 bitmask는 후속 설계 |


## /alatus/shadow_mission 서비스

Type: std_srvs/srv/SetBool. Server: mission. Client: CLI 또는 ros_smoke.

| 방향/필드 | 타입 | 계약 |
|---|---|---|
| Request.data | bool | true=분석 시작 요청; false=중단 및 ABORT reset |
| Response.success | bool | 요청 수락 여부. ABORT에서 true 요청은 false. 실행 성공/표적 획득/비행 허가를 보장하지 않음 |
| Response.message | string | 현재 고정된 설명; 세부 상태는 mission_state에서 확인 |

수락 응답 후 상태 변화는 다음 timer에서 관찰할 수 있습니다. true 요청 직전에 status가 없으면 다음 tick에서 ABORT가 될 수 있습니다.
여러 client가 동시에 start/stop하면 최종 처리 순서에 의존합니다. 현재 인증·소유권·request_id는 없습니다.
mock 연습은 운영자 client 하나만 사용하며 제어권 중재가 구현됐다고 주장하지 않습니다.

## PX4 입력 topic

후보: /fmu/out/vehicle_status_v1, type px4_msgs/msg/VehicleStatus, source PX4/Agent, sink px4_status.
topic의 실제 이름/type/QoS는 ros2 topic list -t 및 info -v로 확인합니다. PX4 내부 boot time과 DDS의 시간 보정을 구분하고 수신 timestamp의 clock 기준을 실제 설정으로 확인합니다.
adapter가 사용하는 원본 필드: timestamp, arming_state, ARMING_STATE_ARMED 상수, failsafe, nav_state.
수신이 끊겨도 마지막 값을 주기적으로 재발행하지 않습니다. consumer가 0.5초 age를 넘으면 invalid로 취급합니다.
version suffix는 MESSAGE_VERSION 기반입니다.
[PX4 v1.16 공식 message version 문서](https://docs.px4.io/v1.16/en/ros2/px4_ros2_msg_translation_node)

## 후속 계약 변경 설계 — 미구현

* perception v2: class_id, bbox, camera_id, capture sequence, exposure timestamp 및 track ID 정책 검토.
* 상태 v2: 자세/위치/속도/airspeed 각각의 timestamp·quality·frame·validity 필요. VehicleStatus에서 이들을 만들지 않음.
* fault v2: 원인 bitmask/enum, observation age, receipt gap, source mismatch, clock fault 기록.
* 현재 AircraftStatus에 position/airspeed를 0으로 채워 넣는 방식은 금지. 별도 typed 메시지와 노드 통합 설계 후 확장.
* v2는 /alatus/v2/...와 새 msg 타입 후보로 분리; 실제 이름은 공통 인터페이스 검토에서 확정.

## Timestamp 정정 근거

uORB 메시지 정의의 boot timestamp 주석만으로 ROS 수신 timestamp의 기준을 확정하지 않습니다.
v1.16.0은 DDS 송신에서 time_offset을 serializer에 전달하고 timestamp/timestamp_sample을 보정합니다.
[PX4 공식 serialization template](https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.16.0/Tools/msg/templates/ucdr/msg.h.em)
