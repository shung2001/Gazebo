# INHA ALATUS ROS 2 v0.4

**Source Ready 실험 기반. 실비행 승인 소프트웨어가 아닙니다.**

v0.3 실제 소스를 보존하고 YOLO 입력 Adapter, Kalman 추정, Camera Geometry, PD/PID Course/Lookahead 유도, MAVROS 상태 변환, 별도 SITL 위치 송신 경로를 추가했습니다. 기본값은 Shadow이며 Onboard Control은 제공하지 않습니다.

## 현재 검증 수준

| Level | 결과 |
|---|---|
| 1 Source Ready | 구현 파일 및 순수 Python 검증 완료 |
| 2 ROS Validated | NOT TESTED — Humble 런타임 미설치 |
| 3 SITL Shadow | NOT TESTED — PX4/Gazebo 미실행 |
| 4 Closed-loop SITL | NOT TESTED — 실제 물리 응답 미검증 |
| 5 Onboard Observer | NOT TESTED — Pi/Hailo/Camera 미실행 |
| 6 Flight Ready | 달성하지 않음; 별도 실기체 개발/시험 필요 |

실제 YOLO11m 가중치/영상/HEF/Camera Calibration/기체 공력/Net Geometry/Gain은 제공되지 않았습니다. 해당 의존 시험은 BLOCKED입니다. Mock 숫자는 시험 Fixture이며 ALATUS 비행 파라미터가 아닙니다.

## 가장 먼저 실행

Ubuntu 22.04에서 ZIP의 이 폴더를 VS Code로 엽니다. ROS가 이미 설치되어 있어도 새 작업공간을 빌드하고 매 터미널에서 Overlay를 source해야 합니다.

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
sudo apt update
sudo apt install -y python3-pytest python3-numpy python3-yaml
bash tools/test_v04.sh
```

Humble/MAVROS 설치 및 ROS 검증:

```bash
# 필요한 패키지 설치 절차는 docs/walkthrough/02_ENVIRONMENT_KO.md 참조
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
bash tools/validate_humble_v04.sh
```

테스트 스크립트는 종료 시 Launch도 정리합니다. 이후 지속 관찰:

```bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
ros2 launch alatus_bringup mock_shadow.launch.py
```

다른 터미널에서도 같은 작업경로/source/export 후:

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /alatus/track_estimate --once
ros2 topic echo /alatus/visual_command --once
ros2 topic echo /alatus/safety_status --once
```

Mock에서 제안이 유효해져도 control_allowed는 false입니다. 오류가 나면 ROS 재설치보다 source 경로, 첫 빌드 오류, 실제 메시지 Python import부터 확인합니다.

## 문서 읽는 순서

1. [마이그레이션](docs/walkthrough/01_MIGRATION_KO.md)
2. [Ubuntu/Humble/MAVROS](docs/walkthrough/02_ENVIRONMENT_KO.md)
3. [YOLO/Kalman](docs/walkthrough/03_VISION_KALMAN_KO.md)
4. [Geometry/Guidance/PID](docs/walkthrough/04_GUIDANCE_PID_KO.md)
5. [PX4/Gazebo 기본 비행](docs/walkthrough/05_PX4_GAZEBO_KO.md)
6. [Vision/Closed-loop SITL](docs/walkthrough/06_VISION_SITL_KO.md)
7. [Pi Onboard Shadow](docs/walkthrough/07_ONBOARD_KO.md)
8. [Git/GitHub](docs/walkthrough/08_GIT_GITHUB_KO.md)

각 문서는 목적/사전조건/실행환경/명령/코드파일/예상출력/성공판정/오류/해결/다음단계의 10개 항목으로 작성했습니다.

설계 근거는 [아키텍처](docs/ARCHITECTURE_KO.md), [변경사항](docs/V04_CHANGELOG_KO.md), [MAVROS 검토](docs/MAVROS_PX4_INTERFACE_KO.md), [논문 검토](docs/REFERENCES_AND_PAPERS_KO.md), [Message Contract](docs/TOPIC_FIELD_CONTRACTS_KO.md)를 참고합니다.

**검증 상태:** [VALIDATION](docs/VALIDATION.md), [Known Issues](docs/KNOWN_ISSUES.md), validation/local-tests.txt, validation/verification_matrix.csv. 실제 측정값 없이 FPS/정확도/비행성능을 보고하지 않습니다.

## 소스 구조와 보존

- src/alatus_interfaces: 기존 6개 + 신규 5개 메시지
- src/alatus_runtime: v0.3 순수 Mission/ClockGuard 및 기존 진단 실행
- src/alatus_bringup: 실행 모드별 Launch
- src/alatus_vision: 순수 수학 + Perception/Pipeline 노드
- src/alatus_mavros: 상태 변환 + 별도 SITL Sender
- regression/v03: 원본 v0.3 전체, COLCON_IGNORE
- legacy_alatus_px4_status: 선택적 DDS 코드, 기본 빌드 제외
- config, sim, deploy, tools, tests, .github: 설정/시뮬레이션/이식/검증/협업

기존 ~/PX4-Autopilot v1.16은 보존합니다. 새 경로 ~/PX4-Autopilot-v1.17.0만 사용합니다. PX4 소스, 학습 가중치, 영상, HEF, 비행 로그, 인증정보는 Repository에 포함하지 않습니다.
