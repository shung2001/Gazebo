# v0.4 검증 결과

실행 환경: 제공자 Linux / Python 3.12.14. Ubuntu 22.04 / Python 3.10 / ROS Humble 환경이 아니다. /opt/ros, PX4, Gazebo, Docker, Pi/Hailo, 실제 사용자 모델이 없다. ROS 패키지를 만든 것과 실제 ROS에서 빌드한 것은 구분한다.

현재 달성: **Level 1 — Source Ready**. Level 2~5는 NOT TESTED 또는 필수 입력 BLOCKED다. Level 6 Flight Ready는 달성하지 않았다.

- 신규 pytest: **83개 PASS** (Python 3.12.14, 합성/해석값/정적 계약 시험).
- 보존 v0.3 회귀시험: 40개 PASS.
- Python compileall, bash -n, package/msg/launch 정적 검사: 실행 로그 참조.
- 순수 수학 시험은 합성 입력/해석값 비교이며 비행 성능 측정이 아니다.
- 첫 로컬 시험은 pytest 미설치로 실행 실패했고, 의존성 설치 후 재실행했다. 중간 실행 실패를 비행 알고리즘 FAIL로 오인하지 않는다.
- CI 파일은 준비했지만 GitHub에서 실행하지 않았다.

재현 명령:

```bash
bash tools/test_v04.sh
# 실제 Humble 환경에서만
bash tools/validate_humble_v04.sh
```

PASS/FAIL/NOT TESTED/BLOCKED의 의미: PASS는 적힌 근거 범위에서 실제 확인, FAIL은 실제 수행 결과 불일치, NOT TESTED는 환경/시험 미수행, BLOCKED는 필수 입력이 없어 진행 불가다. 단순 소스 존재는 런타임 PASS가 아니다. 최종 실행에서 알고리즘 시험 FAIL은 없으며 미검증 상태는 아래와 같다.

| 범위 | 시험 | 상태 | 근거 | 다음 조치 |
|---|---|---|---|---|
| Source | Python syntax | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | ROS manifest XML | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | Message generation declaration list | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | Legacy message byte preservation | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | Legacy core preservation | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | Launch sender isolation | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | YAML installation copies | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Source | SDF XML syntax | PASS | tests/test_contracts.py + compileall | Run ROS build and runtime acceptance separately |
| Perception | Invalid detection | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | Empty detection | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | Multiple candidate ambiguity | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | Confidence/class filtering | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | Bounding box boundaries | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | Missing model refusal | PASS | tests/test_algorithms.py | Validate actual trained model/video |
| Perception | YOLO11m model load | BLOCKED | No supplied model/HEF/video and no device | Supply trusted weights, class mapping, footage, SDK and real hardware |
| Perception | Video Replay actual inference | BLOCKED | No supplied model/HEF/video and no device | Supply trusted weights, class mapping, footage, SDK and real hardware |
| Perception | Gazebo image inference | BLOCKED | No supplied model/HEF/video and no device | Supply trusted weights, class mapping, footage, SDK and real hardware |
| Perception | Hailo HEF inference | BLOCKED | No supplied model/HEF/video and no device | Supply trusted weights, class mapping, footage, SDK and real hardware |
| Tracking | Constant target | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Moving target | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Noisy detections | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Short dropout prediction | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Long dropout timeout | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Outlier rejection | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Covariance growth | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Variable dt | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Reset/reacquire | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Invalid/duplicate timestamp | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Source change reconfirm | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Analytic F/Q prediction | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Tracking | Analytic scalar measurement update | PASS | tests/test_algorithms.py; synthetic inputs only | Measure real imagery RMSE/association |
| Guidance | Target left/right/center | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Target above/below | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Invalid bearing/calibration | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Invalid aircraft fields | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Different speed | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Kinematic bank diagnostic limit | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Target lost reset | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Optical/FLU/ENU sign | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Quaternion yaw transform | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| Guidance | Net ray/plane calculation | PASS | tests/test_algorithms.py; pure functions | Verify real frames/calibration and physical response |
| PID | Zero/positive/negative error | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Step proportional response | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Derivative filter | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Integral anti-windup | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Slew/magnitude saturation | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Reset/disable | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | NaN/Infinity | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| PID | Irregular/invalid dt | PASS | tests/test_algorithms.py | Tune actual PX4 test model; no flight gains approved |
| Safety | Unreviewed permit denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Disconnected/unarmed/invalid field denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Manual mode denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Stale command/state denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Track lost denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Low airspeed denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Safety | Target altitude denial | PASS | tests/test_algorithms.py pure permission logic | ROS service and live router/link validation |
| Regression | v0.3 existing 40 unit/structure/protocol tests | PASS | validation/local-tests.txt | Preserve baseline; ROS runtime not covered |
| MAVROS/PX4 source review | PositionTarget ROS2 API | PASS | docs/MAVROS_PX4_INTERFACE_KO.md; external-dependencies.json | Compare installed binary and test response |
| MAVROS/PX4 source review | ENU/NED conversion code | PASS | docs/MAVROS_PX4_INTERFACE_KO.md; external-dependencies.json | Compare installed binary and test response |
| MAVROS/PX4 source review | PX4 v1.17 receive path | PASS | docs/MAVROS_PX4_INTERFACE_KO.md; external-dependencies.json | Compare installed binary and test response |
| MAVROS/PX4 source review | FW position consumption | PASS | docs/MAVROS_PX4_INTERFACE_KO.md; external-dependencies.json | Compare installed binary and test response |
| MAVROS/PX4 source review | v1.17 tag and Gazebo gitlink | PASS | docs/MAVROS_PX4_INTERFACE_KO.md; external-dependencies.json | Compare installed binary and test response |
| ROS2 | Humble colcon build | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Custom message generation/import | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Launch execution | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Mock ROS integration acceptance | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Replay ROS integration | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Topic/QoS compatibility | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Clock freeze live runtime | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| ROS2 | Duplicate publishers live runtime | NOT TESTED | No /opt/ros in execution host | bash tools/validate_humble_v04.sh on Ubuntu 22.04 or run GitHub CI |
| MAVROS runtime | Connection | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | State receive | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Mode detection | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Position/attitude receive | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Timeout/disconnect/reconnect | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Message type match | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Router parameter confirmation | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| MAVROS runtime | Serial link | NOT TESTED | MAVROS not installed | Run separate SITL/serial workflows and record topic types/ages |
| SITL | PX4 v1.17 build | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Advanced Plane physics/model load | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Sensor state | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Basic fixed-wing takeoff/flight | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Turn and altitude response | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | MAVROS state | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Shadow integration | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Camera rendering/bridge | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Closed-loop response | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Offboard loss/failsafe | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| SITL | Manual mode takeover | NOT TESTED | PX4/Gazebo unavailable in execution host | Follow docs/walkthrough/05 and 06; do not mark PASS before logs |
| Onboard | Docker AMD64/ARM64 build | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | Pi Humble runtime | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | Camera Module 3 | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | HailoRT/Driver/DFC/Model Zoo compatibility | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | YOLO11m HEF compile and inference | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | MAVROS UART | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| Onboard | Logging/CPU/RAM/latency | NOT TESTED | No Pi/Hailo/Camera/Docker runtime | Follow 07 on actual hardware; model dependencies separately BLOCKED |
| GitHub | Workflow actual hosted execution | NOT TESTED | Files prepared, remote not created | User creates private repo and executes workflow |
| GitHub | Private repo push | NOT TESTED | Files prepared, remote not created | User creates private repo and executes workflow |
| GitHub | PR/merge | NOT TESTED | Files prepared, remote not created | User creates private repo and executes workflow |
| Flight | Net Capture geometry | BLOCKED | Mass/aerodynamics/calibration/net survey/gains missing | Separate engineering/ground/flight acceptance; not v0.4 source acceptance |
| Flight | ALATUS aerodynamic model | BLOCKED | Mass/aerodynamics/calibration/net survey/gains missing | Separate engineering/ground/flight acceptance; not v0.4 source acceptance |
| Flight | Real flight authority approval | BLOCKED | Mass/aerodynamics/calibration/net survey/gains missing | Separate engineering/ground/flight acceptance; not v0.4 source acceptance |
