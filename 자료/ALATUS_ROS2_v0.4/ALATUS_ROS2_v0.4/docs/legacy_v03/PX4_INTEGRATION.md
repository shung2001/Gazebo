> 이 파일은 v0.1/v0.2 설계 이력입니다. 현재 v0.3 실행·파라미터·PX4 SHA 설정은 IMPLEMENTED_PARAMETERS_V03_KO.md와 RPI_DOCKER_WALKTHROUGH_KO.md가 우선합니다.

# 선택적 PX4 상태 수신 — 아직 통합 시험하지 않음

이 adapter는 **VehicleStatus 하나만** 구독합니다. 자세·위치·속도·airspeed·estimator·RC override는 수신하지 않습니다.
따라서 firmware가 armed라고 말하는 것과 비행 준비 완료는 다릅니다. 모드 이름만으로 수동 개입 여부를 추론하지 않습니다.

## 의도적으로 좁은 버전 gate

수용 조건은 firmware 선언 `v1.16.0`, px4_msgs 선언 `release/1.16`, 명시적 `contract_reviewed=true`,
생성된 `VehicleStatus.MESSAGE_VERSION == 1`입니다. 그 외에는 예외로 종료합니다.
실제 코드의 gate는 local unit test와 동일한 `alatus_runtime.core.check_px4_gate`입니다.

이 조건은 **실제 PX4 펌웨어 자동 감지/서명/호환성 증명 기능이 아닙니다.**
사용자가 잘못 선언하거나 같은 MESSAGE_VERSION의 다른 wire schema를 설치한 경우를 검출하지 못합니다.
release branch는 이동 가능하므로 양쪽 commit hash를 현장에서 기록하고 필드·DDS mapping을 대조해야 합니다.
v1.17이나 main을 사용하려면 contract를 새로 검토·개발·시험해야 하며 문자열만 바꾸지 마십시오.

[v1.16 VehicleStatus 원본](https://raw.githubusercontent.com/PX4/px4_msgs/release/1.16/msg/VehicleStatus.msg)은
MESSAGE_VERSION=1, uORB에서 boot microseconds로 정의된 timestamp, arming_state, nav_state, failsafe를 정의합니다. 다만 DDS 직렬화 시 timestamp에 time offset이 더해질 수 있으므로 ROS 수신값을 무조건 boot time으로 해석하지 않습니다.
[v1.16.0 DDS mapping](https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.16.0/src/modules/uxrce_dds_client/dds_topics.yaml)은
VehicleStatus를 export 대상으로 지정합니다. YAML의 기본 이름과 실제 DDS의 version suffix를 구분하십시오.

v1.16부터 message versioning이 있으므로 버전된 topic에는 `_vN` suffix가 사용될 수 있습니다.
이 adapter의 기본 후보는 `/fmu/out/vehicle_status_v1`이며 실제 namespace와 type을 반드시 확인합니다.
translation node를 사용하면 다른 버전 간 변환 구성이 가능하지만 이 스타터는 이를 설치·검증하지 않습니다.
[공식 message translation 문서](https://docs.px4.io/v1.16/en/ros2/px4_ros2_msg_translation_node)

## 준비 체크 — 실제 시험 담당자가 수행

1. PX4 v1.16.0 source/firmware hash 및 board DDS client 활성 여부 확보.
2. 해당 PX4 기준으로 Agent를 설치하고 Client 연결 확인. Agent 최신판을 임의 혼용하지 않음.
3. 별도 workspace에서 px4_msgs release/1.16을 확보하고 hash 기록. field 정의를 실제 펌웨어와 비교.
4. Humble 아래에서 px4_msgs를 빌드하고 source한 뒤 ALATUS workspace를 빌드/source.
5. `ros2 topic list -t`와 `ros2 topic info -v <실제 상태 토픽>`으로 이름·타입·QoS 확인.
6. `ros2 topic echo <실제 상태 토픽> px4_msgs/msg/VehicleStatus --qos-reliability best_effort --once`로 값 확인.

위 명령의 `<실제 상태 토픽>`은 발견한 이름으로 대체합니다.
namespace/domain/네트워크를 실제 Client/Agent와 맞춥니다. mock 연습의 localhost/domain42 설정은 PX4 발견을 막을 수 있습니다.
QoS와 시간 동기화는 [공식 ROS 2 가이드](https://docs.px4.io/v1.16/en/ros2/user_guide)를 따릅니다.

## 상태 어댑터만 실행

기본 launch를 종료합니다. **mock_status와 동시 실행하지 않습니다.**
앞 단계의 계약을 실제로 검토한 담당자만 다음을 실행합니다(파일을 수정하지 않고 CLI parameter로 검토 사실 지정).

```bash
ros2 run alatus_px4_status px4_status --ros-args   -p firmware_tag:=v1.16.0   -p px4_msgs_ref:=release/1.16   -p contract_reviewed:=true   -p status_topic:=/fmu/out/vehicle_status_v1
```

별도 launch를 사용할 수도 있습니다. 기본값은 검토 미완료이므로 거절됩니다.
검토 후에만 `ros2 launch alatus_px4_status status_only.launch.py firmware_tag:=v1.16.0 px4_msgs_ref:=release/1.16 contract_reviewed:=true`로 실행합니다.
`ros2 topic echo /alatus/aircraft_status --once`로 source·timestamp·armed·nav_state·failsafe를 비교합니다.
수신이 멈추면 adapter는 새 메시지를 내지 않습니다. consumer의 0.5초 freshness가 만료되어야 합니다.

## Gazebo·실기체 경계

이 ZIP은 PX4 SITL, Gazebo 모델, Agent, ros_gz_bridge를 실행하지 않습니다.
PX4가 simulator와 연결하는 경로와 ROS가 PX4 DDS 상태를 읽는 경로는 서로 다릅니다.
camera 및 /clock에는 별도 simulator bridge가 필요할 수 있습니다. Humble 기본 Gazebo 조합과 PX4 권장 조합이 자동 일치하지 않습니다.
시뮬레이터 버전은 선택한 firmware의 공식 설치 절차와 맞추고, 모델·센서·clock·physics를 별도로 검증하십시오.

header는 **ROS 수신 시각**이며 px4_timestamp_us는 수신한 PX4 timestamp를 그대로 보관합니다. DDS 시간 동기화 오프셋이 적용될 수 있습니다. 이 adapter는 추가 변환이나 네트워크 지연 검출을 구현하지 않았습니다.
기체 readiness unknown은 그대로 유지해야 합니다. 향후 비행용 adapter는 필드별 유효성·센서 quality·time sync·독립 watchdog이 필요합니다.
실제 제어 코드는 이 프로젝트에 없습니다. 상태 수신 성공을 기체 제어 검증으로 기록하지 마십시오.
