> 이 파일은 v0.1/v0.2 설계 이력입니다. 현재 v0.3 실행·파라미터·PX4 SHA 설정은 IMPLEMENTED_PARAMETERS_V03_KO.md와 RPI_DOCKER_WALKTHROUGH_KO.md가 우선합니다.

# Mock 검증 이후 Walkthrough v0.2

이 문서는 기존 WALKTHROUGH_KO.md의 기본 빌드·Mock smoke를 통과한 다음 단계입니다.
모든 실행 명령은 **Ubuntu 22.04 / ROS 2 Humble의 bash**에서 수행합니다.
제작 PC에서는 ROS 2·PX4·Gazebo를 실행하지 못했으므로 아래는 현장에서 실행할 검증 절차입니다.
명령이 제공되어 있다는 사실과 해당 환경에서 성공했다는 사실은 다릅니다.

## 단계 0 — 현재 환경과 증거 보관

이 문서의 workspace 경로는 기존 문서와 같습니다. 새 ZIP을 다른 폴더에 풀었다면 실제 경로를 사용하십시오.
기존 workspace와 새 버전을 덮어 섞지 말고 새 빈 폴더에서 빌드하십시오.

```bash
cd ~/alatus_delivery/ALATUS_ROS2_STARTER
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=1
mkdir -p evidence/session-01
lsb_release -ds
python3 --version
printenv ROS_DISTRO
python3 tools/run_local_tests.py
colcon test-result --verbose
```

evidence/session-01은 현장 기록 폴더입니다. 환경 정보·테스트 출력은 복사하거나 로그 파일로 보관합니다.
새 배포본은 기존 14개 로직/구조 검사에 4개 설계 대조 검사를 추가합니다. 현재 run_local_tests.py의 기대 개수는 18개입니다.
colcon test는 별도 수집 경로이므로 같은 개수를 기대하지 않습니다.

## 단계 1 — 실제 설정과 설계안을 구분해서 확인

기본 launch를 터미널 A에서 실행합니다.

```bash
ros2 launch alatus_bringup shadow.launch.py
```

터미널 B도 단계 0과 동일하게 source/domain 설정을 한 뒤:

```bash
ros2 param list /mock_perception
ros2 param get /mock_perception dropout
ros2 param get /mission use_sim_time
ros2 param dump /mock_perception
ros2 topic info /alatus/aircraft_status -v
```

기대: dropout=false, use_sim_time=false. aircraft_status publisher는 mock_status 하나입니다.
프레임워크가 제공하는 다른 파라미터가 보일 수 있습니다. ALATUS application parameter와 구분합니다.
DETAILED_NODE_DESIGN_KO.md에서 proposed_not_implemented로 표시된 값은 현재 param list에 없습니다.
`publish_rate_hz`, `confirm_hits`, `diagnostic_gain` 등을 현재 적용 가능한 YAML 값으로 사용하지 마십시오.

**완료 기준:** 실제 선언값과 문서의 implemented 목록이 일치하고, source publisher 하나를 확인했습니다.

## 단계 2 — 기본 통신과 고장 주입 결과를 기록

새 IDLE launch에서:

```bash
python3 tools/ros_smoke.py
ros2 topic hz /alatus/detection
```

hz 명령은 잠시 관찰하고 Ctrl+C로 종료합니다. 10 Hz는 타이머 목표이며 정확한 실시간 보장이 아닙니다.
느리면 프로세스 부하·WSL 상태·clock·DDS를 점검합니다. 무조건 timeout을 늘려 숨기지 않습니다.

필요하면 rosbag2 설치 후 별도 터미널에서 기록합니다.

```bash
ros2 bag record -o evidence/session-01/mock_faults /alatus/detection /alatus/target_track /alatus/aircraft_status /alatus/mission_state /alatus/guidance_proposal /alatus/safety_status
```

동일한 bag 출력 경로를 반복 사용하지 말고 다음 시험에는 새 이름을 지정합니다.

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

잠시 기다린 뒤 mission과 safety를 확인합니다.

```bash
ros2 topic echo /alatus/mission_state --once
ros2 topic echo /alatus/safety_status --once
ros2 param set /mock_perception dropout true
```

다시 잠시 기다린 뒤 ABORT, proposal.valid=false, control_allowed=false를 확인합니다.
다음으로 dropout=false를 적용하고 3회 이상 정상 관측이 들어올 시간을 준 뒤 true 요청만 보냅니다.

```bash
ros2 param set /mock_perception dropout false
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

기대: ABORT에서는 요청이 거절됩니다. 다음과 같이 reset 후 다시 시작합니다.

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: false}'
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

**완료 기준:** 고장과 회복 후에도 gate가 제어를 허가하지 않으며 ABORT reset 정책을 재현했습니다.

## 단계 3 — 노드를 분리해 발행 중단을 시험

기본 launch를 Ctrl+C로 종료합니다. 남은 프로세스 여부를 node list로 확인합니다.
아래 각 행을 **별도의 터미널**에서 실행합니다. 각 터미널에 source/domain 설정이 필요합니다.

| 터미널 | 실행 명령 |
|---|---|
| A | `ros2 run alatus_runtime mock_perception` |
| B | `ros2 run alatus_runtime tracker` |
| C | `ros2 run alatus_runtime mock_status` |
| D | `ros2 run alatus_runtime mission` |
| E | `ros2 run alatus_runtime guidance` |
| F | `ros2 run alatus_runtime safety_gate` |
| G | 관찰·서비스·bag 명령 |

1. 초기 메시지가 흐르는지 확인 후 shadow_mission true를 요청합니다.
2. TRACK_SHADOW를 확인한 뒤 A의 mock_perception을 Ctrl+C로 종료합니다.
3. source 관측 시간이 0.5초를 넘으면 tracker.valid=false, mission=ABORT가 기대됩니다.
4. A를 다시 실행해도 ABORT가 유지되는지 확인하고 false/true로 reset합니다.
5. 이번에는 C의 mock_status를 중단합니다. status freshness 만료로 ABORT가 되어야 합니다.
6. C 복구 후 false/true reset; 다음에는 E의 guidance를 중단합니다.
7. safety 입력이 만료되어 inputs_valid=false가 되어야 합니다. Mission은 현재 guidance/safety 결과를 구독하지 않으므로 TRACK_SHADOW로 남을 수 있습니다.

0.5초는 기본 age 기준입니다. 실제 관찰은 노드 주기·스케줄링·CLI 지연 때문에 그 뒤에 보입니다.
현재는 ROS clock 기반이며 독립 monotonic watchdog이 아닙니다.

**완료 기준:** target loss, status loss, proposal loss가 서로 다른 경로로 검출됨을 기록했습니다.
SafetyGate 프로세스 자체가 죽으면 SafetyStatus가 사라질 뿐이며 외부 감독자가 현재 구현되어 있지는 않습니다.

## 단계 4 — 실제 인식 결과를 연결하기 위한 준비

이 단계는 detector bridge가 아직 없으므로 **설계 및 구현 후 시험할 절차**입니다.
특정 YOLO 패키지 설치 명령이나 카메라 topic 이름을 임의로 가정하지 않습니다.

먼저 A 담당자가 다음 자료를 확보합니다.

* 카메라 드라이버/모델, 실제 image topic/type, 해상도·FPS·encoding·노출 timestamp 기준.
* detector 패키지/commit, 실제 output type와 필드, confidence 의미, class map.
* 카메라 intrinsics/distortion, 장착 extrinsics, 처리·통신 지연 측정 방법.
* 표적이 여러 개일 때 선택·ID 유지·동점·가림 후 재확인 정책.

그다음 detection_bridge가 다음 변환을 하도록 구현합니다.

1. 실제 detector의 bbox centre (u,v)와 해당 이미지 W,H를 읽습니다.
2. W,H>0 및 좌표 범위를 확인하고 x=u/W, y=v/H로 변환합니다.
3. 원 image exposure stamp를 복사합니다. detector 처리 종료 시간을 관측 시각으로 쓰지 않습니다.
4. 표적 선택과 stable target ID 정책을 적용합니다. confidence가 가장 높다는 사실만으로 같은 물체임을 가정하지 않습니다.
5. TargetDetection을 reliable/volatile/depth10으로 발행합니다. valid=false와 무발행의 정책을 구분합니다.
6. 잘못된 bbox·class·stamp·NaN·낮은 confidence는 invalid로 처리하고 로그에 원인을 남깁니다.

시험 시 단계 3 구성에서 mock_perception만 제외하고 새 bridge를 실행합니다.
현재 고정 frame은 camera_optical이므로 실제 frame에 맞게 계약을 변경하려면 tracker/guidance/gate도 함께 수정해야 합니다.
실제 frame을 속여서 TF가 구현됐다고 설명하지 마십시오. 현재 계산에는 body frame 변환이 없습니다.

**완료 기준:** recorded image와 detection/track의 위치·ID·노출 시각을 대조하고, 표적 상실·지연·다중표적 시험을 통과합니다.
이것은 인식 연결 검증이며 고정익 유도 성능 검증이 아닙니다.

## 단계 5 — PX4 상태만 읽기

기체 제어 송신은 하지 않습니다. 먼저 SITL 등 별도 시험 환경에서 읽기 경로를 확인합니다.
선택 계약은 v1.16.0 / px4_msgs release/1.16 / VehicleStatus MESSAGE_VERSION=1입니다.
현재 최신 버전이라는 뜻이 아니라 이 starter가 좁게 검토하는 계약이라는 뜻입니다.

firmware와 px4_msgs의 source commit 및 message schema를 직접 확인합니다.
서로 다른 workspace에서 빌드한 px4_msgs overlay가 섞이지 않도록 새 터미널을 사용합니다.

예시 source 순서(해당 경로에 실제 workspace를 준비한 경우만 실행):

```bash
source /opt/ros/humble/setup.bash
source ~/px4_msgs_ws/install/setup.bash
source ~/alatus_delivery/ALATUS_ROS2_STARTER/install/setup.bash
```

PX4 Client/Agent의 domain과 네트워크 설정을 확인한 뒤 ROS 설정을 맞춥니다.
기존 연습의 ROS_DOMAIN_ID=42를 PX4가 자동으로 따르지는 않습니다.
아래는 기본 domain0의 같은 PC SITL을 선택한 경우의 ROS 측 예시입니다.

```bash
export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY
ros2 daemon stop
ros2 topic list -t
```

이 설정만으로 PX4 Client/Agent의 네트워크·domain 구성이 완료되는 것은 아닙니다.
다른 PC의 실기체 연결을 포함해 transport/port/namespace를 별도로 확인하십시오.

실제 topic이 /fmu/out/vehicle_status_v1인 경우:

```bash
ros2 topic info /fmu/out/vehicle_status_v1 -v
ros2 topic echo /fmu/out/vehicle_status_v1 px4_msgs/msg/VehicleStatus --qos-reliability best_effort --once
```

다른 이름이면 발견된 실제 이름으로 바꿉니다. 값이 안 보이면 gate를 우회하지 말고 Agent/Client/schema/QoS/domain부터 확인합니다.
해당 버전 공식 가이드는 Agent v2.4.3 예시를 제공하며 최신 Agent를 임의로 혼합하지 않습니다.
[PX4 v1.16 ROS 2 가이드](https://docs.px4.io/v1.16/en/ros2/user_guide)

계약 검토가 끝난 뒤에만:

```bash
ros2 launch alatus_px4_status status_only.launch.py firmware_tag:=v1.16.0 px4_msgs_ref:=release/1.16 contract_reviewed:=true
```

다른 터미널에서:

```bash
ros2 topic info /alatus/aircraft_status -v
ros2 topic echo /alatus/aircraft_status --once
```

기대: publisher는 px4_status 하나; source=PX4_VEHICLE_STATUS_ONLY; PX4와 armed/nav_state/failsafe 일치.
flight_ready_known와 manual_override_known는 false가 정상입니다.
상태 어댑터와 함께 Mock 분석을 시험하려면 단계 3에서 mock_status를 제외하고 나머지 다섯 노드를 실행합니다.
모든 노드를 선택한 같은 domain/source/clock 환경으로 맞춥니다. PX4가 failsafe라면 Mission 시작 후 ABORT가 정상일 수 있습니다.
failsafe를 숨기기 위해 mock_status를 병렬 실행하지 않습니다.

**완료 기준:** 정상 수신·중단·재연결, raw PX4 상태 비교, source publisher 하나, 제어 송신 없음의 근거를 남깁니다.

## 단계 6 — Gazebo에서의 관찰 통합

이 단계는 Gazebo/PX4/모델 설치 완료 후 수행합니다. starter는 simulator나 Agent를 제공하지 않습니다.
[선택한 v1.16 Gazebo 공식 문서](https://docs.px4.io/v1.16/en/sim_gazebo_gz/)에 맞춰 환경을 준비합니다.
고정익 모델 target 이름은 실제 checkout에 존재하는지 확인한 뒤 선택합니다.
문서에 없는 `gz_advanced_plane` target을 무조건 실행하라고 가정하지 않습니다.

시험 순서는 다음과 같습니다.

1. 선택 firmware source SHA, Gazebo 버전, model commit, airframe 설정, world, sensor 설정을 기록합니다.
2. ROS와 분리된 PX4/SITL 상태에서 모델이 뜨고 센서·상태가 정상인지 확인합니다.
3. 단계 5의 read-only 상태 어댑터를 연결합니다.
4. model camera가 실제로 제공하는 image/CameraInfo의 topic/type/frame을 찾습니다.
5. 단계 4의 bridge로 인식을 연결하거나, 먼저 mock perception으로 상태 수신 경로만 확인합니다.
6. flight command 없이 image와 상태·timestamp·latency·ABORT를 기록합니다.

시간 정책은 다음 둘 중 하나를 선택하고 섞지 않습니다.

| 정책 | 사용 조건 | 주의 |
|---|---|---|
| OS clock | 기본 학습·실시간에 가까운 simulation | source stamp도 해당 ROS clock과 비교 가능해야 함; simulation rate 변화에 취약 |
| Simulation clock | image/physics와 같은 simulator time이 필요한 시험 | /clock bridge, 모든 ROS 노드 use_sim_time=true, PX4 time sync 설정을 같은 공식 절차에 맞춤 |

두 번째 정책의 경우 ros_gz_bridge가 해당 Gazebo 버전과 호환되어야 합니다.
공식 clock bridge 예시를 bash quoting을 포함해 쓰면 다음과 같습니다.

```bash
ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
```

브리지가 보인 뒤 모든 관련 노드의 use_sim_time을 동일하게 설정해 재시작합니다.
PX4 UXRCE_DDS_SYNCT 설정도 선택 버전의 공식 simulation-time 절차에 맞춰야 합니다.
이는 실제 비행 컨트롤러의 기본 설정을 일괄 변경하라는 지시가 아닙니다.
[PX4 공식 clock 설명](https://docs.px4.io/v1.16/en/ros2/user_guide#ros-gazebo-and-px4-time-synchronization)

현재 ROS timer 기반 freshness는 simulation pause 때 멈출 수 있습니다.
clock rewind/future stamp로 tracker 복구가 지연될 수 있으므로 지금은 시험 run을 종료·재시작하는 정책을 사용합니다.
독립 watchdog/clock reset recovery가 구현되기 전에는 이를 실시간 안전 기능으로 인정하지 않습니다.

**완료 기준:** sim pause/slow/rewind를 포함한 관측 결과와 제한을 기록합니다. 모델의 고정익 폐루프 제어 안정성을 검증했다고 쓰지 않습니다.

## 단계 7 — 실제 유도계 설계로 넘어가기 위한 입력

다음 값은 아직 근거가 없어 숫자를 임의로 고정하지 않습니다.

| 필요한 자료 | 결정할 설계 |
|---|---|
| 표적/회수망 geometry, 허용 접근오차·방향·속도 | mission 성공/실패 조건, 접근 경로 |
| camera intrinsics/extrinsics, 지연, 표적 거리/3D 추정 | image error에서 공간 유도로의 변환 |
| 질량·CG·관성·공력·추진·조종면·속도 범위 | 기동 가능성, 선회반경, 제한 및 saturation |
| 위치/자세/airspeed quality, 개별 timestamp | field별 state validity와 fallback |
| PX4 firmware/library 정확한 commit 및 API | 향후 제어 인터페이스의 별도 구현 설계 |
| RC/운영자 개입, 링크 손실, PX4 failsafe 시험 | 독립 안전/중단/복귀 정책 |

이 자료를 확보한 뒤에만 물리 guidance law와 제어 출력 인터페이스를 별도 검토합니다.
현재 correction_norm을 PX4 명령에 바로 연결하는 단계는 제공하지 않습니다.
