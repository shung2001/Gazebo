# 기술 감사 — 2026-11-02 (Asia/Seoul)

## 근거와 검토 범위

연결된 원 대화 `6ae30d5e-8af4-83ee-8b30-f6c0205e6ba4`의 최근 10개 턴을 읽었습니다.
실제 이전 설계 메시지 `837d85b3-a885-4e06-b7a0-1becbf60da71`을 검토했습니다.
작업 폴더는 시작 시 비어 있었고 대화 조회의 attachments는 비어 있었습니다.
이전 메시지에 링크된 sandbox PDF·Starter ZIP의 파일 본문은 확보하지 못했습니다.
따라서 아래는 **이전 아키텍처 본문 및 공식 문서에 대한 감사**입니다.
기존 프로젝트 소스코드나 PDF 요구사항의 완전한 감사는 완료되지 않았습니다.

## 판정 및 수정

| 이전 주장/설계 | 판정 | 이번 수정 |
|---|---|---|
| 기존 Starter Pack 5개 패키지를 재사용 가능 | 소스 미확보, 검증 불가 | 재사용을 주장하지 않고 새 패키지를 작성 |
| Pixhawk 6C·접이식 주익·회수망 등 프로젝트 조건 | 대화의 맥락일 뿐 원본 요구사항 미확인 | 하드웨어·성능 확정 조건에서 제외 |
| detection과 track, mission과 guidance 분리 | 타당한 설계 선택 | typed 인터페이스와 3회 연속 관측 확인 구현; 실제 다중물체 추적 아님 |
| 픽셀 중심 오차를 heading/bearing 값으로 사용 가능 | 물리적으로 부족 | x−0.5 영상 오차와 무차원 제한값만 출력; 각도 필드 제거 |
| AircraftState에 airspeed·attitude·manual override 포함 | 단일 상태 수신으로 보장 불가 | AircraftStatus는 수신·arming·nav_state·failsafe만; readiness/override는 unknown |
| PX4 어댑터를 초기 필수 노드로 배치 | mock 학습에 불필요한 의존성 | 기본은 mock status; PX4는 별도 수동 실행 |
| PX4 Command Adapter를 초기 비활성으로 구현 | 오설정으로 제어 가능성이 남음 | command adapter 자체를 제공하지 않음; gate 항상 false |
| SafetyStatus를 Mission이 사용 | 피드백 의미·시작 조건 미정 | Mission은 target/status로 판단; gate는 끝단 관찰자; 순환 의존 제거 |
| `/fmu/out/vehicle_status`를 고정 이름으로 사용 | 메시지 버전·namespace별 불충분 | v1.16 MESSAGE_VERSION=1용 `_v1` 후보, 현장 topic/type 확인 필수 |
| Humble만 맞으면 PX4 연결 가능 | 불충분 | PX4 tag, px4_msgs ref, DDS mapping, Agent, QoS, clocks 별도 확인 |
| FW lateral/longitudinal API를 일반 ROS Python 기능처럼 채택 | 버전 및 C++ library 의존성 누락 | 본 프로젝트에는 미사용; v1.17 계열 API는 별도 C++ 통합 과제 |
| gz_advanced_plane로 시작하면 ALATUS 모델 검증 가능 | 소프트웨어 예시일 뿐 모델 동일성 없음 | Gazebo 모델 미포함; 공력·질량·CG·관성·접이식 전개 모델은 별도 검증 |

PX4의 ROS 2 연결은 uXRCE-DDS Client/Agent와 해당 펌웨어에서 노출한 DDS 메시지 계약을 확인해야 합니다.
ROS/PX4의 좌표계와 시간 기준을 혼용하면 안 됩니다. 본 프로젝트는 이미지 좌표만 사용하고 ENU↔NED 변환을 구현하지 않습니다.
[PX4 v1.16 ROS 2 가이드](https://docs.px4.io/v1.16/en/ros2/user_guide)

Offboard는 단순 토픽 연결로 완성되지 않습니다. PX4는 2 Hz를 초과하는 생존 신호를 요구하며 진입 전 스트리밍과 손실 대응이 필요합니다.
MC 예제의 setpoint 동작을 FW에 그대로 일반화하지 않습니다. 본 스타터는 Offboard를 요청하거나 생존 신호를 보내지 않습니다.
[PX4 v1.16 Offboard](https://docs.px4.io/v1.16/en/flight_modes/offboard)

v1.17 공식 Control Interface 문서는 `FwLateralLongitudinalSetpointType`을 설명하지만 일부 문구에는 여전히 planned 표기가 남아 있습니다.
따라서 이전의 “v1.17부터 지원하니 사용 가능”은 구체적 firmware/library commit과 시험 없이는 과도한 보장입니다.
[공식 Control Interface](https://docs.px4.io/v1.17/en/ros2/px4_ros2_control_interface),
[공식 v1.17 릴리스 설명](https://px4.io/px4-autopilot-release-v1-17-what-you-need-to-know/)

custom msg 생성은 독립 ament_cmake 패키지, Python 실행 노드는 ament_python으로 분리했습니다.
[ROS 2 Humble 공식 튜토리얼 원문](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.rst)

## 자료가 확보되면 다시 확인할 항목

1. 요구사항 ID별 성공 조건: 접근 속도/각도, 회수망 크기, 접이식 주익 lock, 운영자 중단 절차.
2. 기존 ZIP의 실제 패키지·topic·state machine과 신규 계약의 차이.
3. 카메라 내·외부 파라미터, 지연, FPS, 표적 ID/크기, 거리 추정 방법.
4. PX4 firmware hash, board config, px4_msgs hash, Agent 버전, Gazebo 버전/model commit.
5. 실속/선회/하중/포화 제한, 상태추정·airspeed 유효성, RC 개입·failsafe의 독립 시험.

현재 결과는 비행 제어계 완성이 아니라 제어 없는 소프트웨어 개발 기반입니다.

## v0.2 추가 정정: PX4 timestamp 해석

이전 설명에서 ROS에서 받은 PX4 timestamp를 무조건 boot microseconds로 설명한 것은 불완전했습니다.
v1.16.0의 DDS 송신 코드는 session time_offset을 serializer에 전달하고, serializer는 timestamp/timestamp_sample에 이를 더합니다.
따라서 이 adapter의 px4_timestamp_us는 **수신 필드 값**이며, boot/agent/simulation clock 기준을 실제 sync 설정과 함께 확인해야 합니다.
이 adapter 자체는 timestamp를 추가 변환하지 않고 header만 ROS 수신 시각으로 생성합니다.
[DDS 송신 공식 소스](https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.16.0/src/modules/uxrce_dds_client/dds_topics.h.em),
[공식 직렬화 template](https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.16.0/Tools/msg/templates/ucdr/msg.h.em)

v0.2는 node별 설정 명세, topic field 계약, 후속 walkthrough, 설계 검토/시험 계획을 추가합니다.
새 파라미터 구현과 위 경계 동작 수정은 아직 수행하지 않았습니다.
