> 이 파일은 v0.1/v0.2 설계 이력입니다. 현재 v0.3 실행·파라미터·PX4 SHA 설정은 IMPLEMENTED_PARAMETERS_V03_KO.md와 RPI_DOCKER_WALKTHROUGH_KO.md가 우선합니다.

# 상세 설계 검토와 다음 구현 계획

v0.2는 문서/설계 개정이며 v0.1 런타임의 동작은 변경하지 않았습니다. AircraftStatus.msg의 시간 설명 주석만 정정했으며 필드·타입은 동일합니다.
기본 코드의 검증된 경로를 유지하면서 상수의 의미, 경계 동작, 후속 구현 순서를 고정합니다.

## 현재 상수와 노드별 검사

| 위치 | 현재 값/정책 | 연결되는 노드 | 변경 시 함께 검토할 대상 |
|---|---|---|---|
| Base.current / fresh 기본 | age<=0.5초, 미래는 거절 | tracker/mission/guidance/safety | 관측·상태·mission·proposal을 별도 timeout으로 분리 |
| observation_ok | confidence>=0.7, x/y [0,1], finite | tracker/mission/guidance | 각 소비자의 중복 검사 일치 |
| Tracker.update | 3회, 같은 ID, 증가하는 stamp, gap<=0.5초 | tracker | source sequence/clock fault 및 invalid handling |
| create_timer | 0.1초 | 기본 여섯 노드 | publish period, age budget, CPU 부하 |
| Mock pattern | x=0.5+0.2sin(now×0.3), y=0.5, confidence=.95, ID1 | mock_perception | centre/amplitude 결합 범위 |
| Mock status | source 고정, received=true, failsafe/armed=false | mock_status | fault injection parameter화 |
| proposal | e=x-.5, clip(-.5e,±.2) | guidance | 무차원 diagnostic만; 실제 유도법과 분리 |
| gate | correction abs<=.200001, control=false | safety_gate | float32 tolerance, independent diagnostics |
| PX4 gate | v1.16.0/release1.16/MESSAGE_VERSION1 | px4_status | hash·schema·topic·QoS, 자동 판별 아님 |

## 알려진 한계와 처리 방침

1. **미래 stamp에 의한 추적 복구 지연:** Tracker는 invalid 미래 관측에서도 더 큰 stamp를 last_stamp에 기록할 수 있습니다.
   이후 정상 stamp가 그 값보다 작으면 거절됩니다. 현재는 run 재시작으로 초기화합니다.
   후속 수정은 accepted observation timestamp와 received timestamp를 분리하고, 거절 입력이 accepted watermark를 바꾸지 않도록 합니다.
2. **clock rewind:** 이전 clock epoch의 상태가 남을 수 있습니다. 후속 설계는 backward jump 감지 → 캐시/확인 횟수 reset → Mission ABORT 유지 → 운영자 재시작 확인입니다.
   clock reset으로 자동 비행 재개하는 정책은 없습니다.
3. **stale track hit count:** timer가 logic.hits만 0으로 바꾸고 마지막 message.consecutive_hits는 남길 수 있습니다.
   현재는 valid/time을 우선합니다. 후속 구현에서 message count도 일치시켜야 합니다.
4. **출처 혼합:** 현재 consumer에 source 문자열 비교나 다중 publisher 검사가 없습니다. publisher 하나라는 운영 검증이 필요합니다.
   후속 expected_status_source와 별도 supervisor를 구현하기 전에는 자동 보호라고 설명하지 않습니다.
5. **상태 최신성:** adapter 수신 stamp가 최신이어도 raw telemetry가 upstream에서 오래되었을 가능성을 이 코드가 검출하지 못합니다.
   수신 timestamp progression·reset·timesync·transport 지연 정책이 필요합니다.
6. **Safety 단방향:** Mission은 SafetyStatus를 구독하지 않습니다. guidance 중단에도 TRACK_SHADOW가 남을 수 있습니다.
   향후 health supervisor를 도입할지, mission에 health 신호를 줄지 별도 설계합니다. gate result를 단순 순환 연결하지 않습니다.
7. **안전 노드 자체 중단:** SafetyStatus 무응답을 보는 외부 watchdog은 없습니다. ROS time 기반 timer는 sim pause를 독립적으로 검출하지 못합니다.
8. **고정 reason 문자열:** 실제 invalid 세부 원인이나 부팅 후 초기상태를 세분화하지 않습니다. 후속 fault enum/bitmask와 reason code를 설계합니다.

이 한계는 비행 제어 기능을 추가하라는 뜻이 아닙니다. 다음 구현 작업의 명시적 검토 목록입니다.

## 시험 ID와 합격 기준

아래 ROS/PX4 시험은 아직 실행하지 않았습니다. 순수 로직에서 일부 조건이 검사되어도 ROS 통신 시험 통과를 뜻하지 않습니다.

| ID | 입력/고장 | 기대 결과 | 수준 / 담당 |
|---|---|---|---|
| L01 | threshold 바로 아래/경계, NaN/Inf/out-of-range | invalid; exception 없는 결정적 로직 | local / A |
| L02 | N-1,N, 중복, ID 변경, gap | N회 확인과 reset 정확 | local / A |
| L03 | 시작, status fault, target loss, reset | 상태 표와 일치; ABORT latch | local / B |
| L04 | 모든 입력 bool 조합, 수치 극값 | control_allowed 항상 false | local / C |
| R01 | 새 기본 launch + smoke | IDLE에서 shadow 시작/종료, diagnostics 확인 | ROS / 공동 |
| R02 | dropout true/false | ABORT 유지; false/true로만 reset | ROS / A+B |
| R03 | perception/status/guidance 프로세스 각각 중단 | freshness 만료, 지정 invalid/ABORT 경로 | ROS / C |
| R04 | 원 관측 stale, 생성된 proposal은 최신 | gate.inputs_valid=false | ROS stimulus 도구 후 / C |
| R05 | wrong frame, future stamp, clock rewind | invalid 및 복구 정책 검증; current limitation과 비교 | ROS stimulus 도구 후 / A+C |
| R06 | 서로 다른 source publisher 두 개 | 현재는 운영에서 발견; 후속 구현은 자동 fault | 후속 source gate 후 / C |
| R07 | 제안 파라미터 구현 후 잘못된 YAML | 시작 실패; 이유 설명; 부분 적용 없음 | 후속 구현 / 담당별 |
| P01 | 잘못된 firmware/ref/version/review | adapter 시작 거절 | 로직+PX4 ROS / C |
| P02 | PX4 raw→adapter 비교 및 수신 중단 | 값 일치, unknown 보존, timeout | PX4 read-only / C |
| G01 | sim /clock 일치, pause, speed change, rewind | clock 정책/제한대로 기록; 제어 송신 없음 | Gazebo 관찰 / 공동 |
| V01 | docs registry와 source/msg 비교 | 선언값·타입·필드가 문서와 일치 | local / C |

## 구현 순서와 분담

1. 공동: 미확인 프로젝트 요구조건을 수집하고 현재 v0.1 메시지 계약을 동결합니다.
2. A: 미래 stamp/clock reset/카운트 일관성 수정안을 테스트와 함께 작성합니다.
3. C: parameter descriptor/validation 공통 모듈을 구현합니다. 현재 dropout 외 신규값은 먼저 startup-only로 제한합니다.
4. A: tracker·mock 파라미터화; B: mission/guidance의 독립 timeout·source 정책; C: gate와 status 파라미터화.
5. 공동: 비정상 YAML, atomic 후보 검증, 모듈별 값 불일치 검사를 통합합니다.
6. C: 깨끗한 Humble 환경에서 build/test 및 R01~R03 확인; A+B가 재현 결과 검토.
7. A: detector 자료 확보 후 bridge 구현; C: 별도 PX4 read-only; B: 실제 guidance 요구조건 명세.
8. 공동: Gazebo 관찰 통합과 clock fault 시험. 실제 제어 기능은 이 계획과 분리하여 새 검토합니다.

## 아직 고정하지 않은 물리 파라미터

airspeed_min/max, stall_margin, bank_limit, approach_angle, recovery_corridor, turn_radius,
flight guidance gain, net location/orientation, launch/deployment dynamics는 자료가 없어 미정입니다.
다른 기체 예제의 값을 ALATUS 확정값으로 가져오지 않습니다. 자료·단위·좌표계·시험 근거를 받은 뒤 설계합니다.

## 검토 근거

* 로컬 src/*.py, msg/*.msg, 기존 AUDIT 및 VALIDATION.
* [ROS 2 Humble Parameters](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Basic/About-Parameters.rst)
* [Humble rclpy Node](https://raw.githubusercontent.com/ros2/rclpy/humble/rclpy/rclpy/node.py)
* [Humble QoS](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)
* [PX4 v1.16 ROS 2](https://docs.px4.io/v1.16/en/ros2/user_guide)
* [PX4 v1.16 message versioning](https://docs.px4.io/v1.16/en/ros2/px4_ros2_msg_translation_node)
* [PX4 v1.16 Gazebo](https://docs.px4.io/v1.16/en/sim_gazebo_gz/)

공식 문서에서 확인한 API/통신 조건과 우리 팀의 제안 기본값은 별개입니다. 공식 출처가 0.5초/3회/gain0.5를 ALATUS에 권장한 것은 아닙니다.
