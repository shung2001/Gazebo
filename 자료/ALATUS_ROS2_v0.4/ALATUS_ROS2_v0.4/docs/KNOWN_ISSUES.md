# 미완료 및 알려진 한계

1. **ROS 빌드/런타임 NOT TESTED**: 소스 문법/단위시험은 실제 rclpy/rosidl/Launch/QoS ABI 검증을 대체하지 않는다. Jammy CI/사용자 PC에서 validate_humble_v04.sh부터 실행한다.
2. **실제 모델 미제공 BLOCKED**: class names, inference shape, input resolution, HEF graph/NMS/latency를 확인하지 못했다. 모델 경로가 없으면 Perception은 실패한다. 모델 자동 다운로드는 없다.
3. **Hailo Adapter 경계만 구현**: 기존 Unix Datagram 결과계약을 사용하며 실제 Hailo SDK 추론·HEF compilation은 구현/검증되지 않았다. 임의 API로 성공 처리하지 않았다.
4. **실제 카메라 내·외부 보정 미제공**: 실환경 Calibration은 false/null이다. Mock calibration/gains는 fixture다. 모델/카메라 보정을 확보하기 전 유도 Invalid가 정상이다.
5. **유도는 Bearing Follow prototype**: Net Plane interception/기체 크기/회수망 충격/terminal guidance/접근가능성·도달시간 계산은 완성하지 않았다. geometry.net_intersection은 계산용 독립 함수다.
6. **Kalman camera motion**: 자세로 LOS는 회전하지만 측정시각 attitude interpolation, Camera derotation, rolling shutter, EKF, delay compensation을 구현하지 않았다. 빠른 기체 회전 시 image CV 모델이 깨질 수 있다.
7. **제어기 부호/튜닝 한계**: +/-pi wrap 경계의 D kick, 실측 지연, 큰 접근각/원근 비선형은 추가 검토가 필요하다. Default 실제 gains=0, limits=0으로 사용 전 검토가 필요하다. 실제 Bank/Pitch/속도 제한은 PX4에서 별도 설정한다.
8. **Failsafe/RC 정보 불완전**: MAVROS State.system_status는 PX4 failsafe_flags 전체가 아니다. manual_input도 Pilot override를 보장하지 않는다. per-field known은 false로 유지한다. SITL Permit은 이를 명시적으로 검토해야 하며 실기체 제어 승인으로 사용할 수 없다.
9. **SITL Sender runtime NOT TESTED**: 실제 설치 MAVROS가 /mavros_router fcu_urls를 제공하는지 확인해야 한다. 모르면 fail-closed다. Local PID+loopback 가드는 하드웨어 attestation이나 보안 경계가 아니다.
10. **SDF/Bridge 물리 런타임 NOT TESTED**: XML 문법만 확인했다. 새 모델/World가 실제 PX4/Gazebo에 로드되고 Sensor/Aero/Actuator가 연결되는지, gz_frame_id/Bridge header와 실제 시각을 확인해야 한다. Net capture 물리모델은 없다.
11. **Domain Gap**: Synthetic 과녁 색/크기와 사용자 dataset이 달라 YOLO가 놓칠 수 있다. 실제 영상과 Synthetic 영상을 별도로 평가한다.
12. **전체 시간 정합**: ROS sim clock, MAVROS timestamps, Camera exposure mapping과 steady receipt를 일치시켜야 한다. Simulator가 0초에 멈춘 상태로 Pipeline을 먼저 켜면 ClockGuard fault가 latch될 수 있다. /clock 진행 후 시작하고 fault 후 전체 Pipeline을 재시작한다.
13. **온보드/ARM64/Docker NOT TESTED**: 기본 Compose는 Serial/Hailo 장치를 추정해 열지 않는다. Host Hailo 결과와 confirmed Serial device/baud/permissions를 준비해야 한다. Dockerfile v04는 GeographicLib 데이터셋 설치가 필요할 수 있어 문서대로 추가해야 한다.
14. **MAVROS heartbeat 속도**: State heartbeat 1 Hz를 고려해 2.5 s까지 상태 연결을 허용하며 다른 critical fields는 0.5 s다. 실제 link loss 감지 지연과 PX4 failover 지연을 함께 측정한다. MAVROS connected만으로 비행 준비 완료를 주장하지 않는다.
15. **관측 Source 단일성**: 동일 Topic에 Mock/DDS/MAVROS를 함께 켜지 않는다. Pipeline/Sender는 중복 Publisher를 차단한다. 구버전 Legacy Launch와 v0.4 Launch를 동시에 켜지 않는다.
16. **기본 비행 Mission 미실행**: QGC에서 시험자가 Takeoff/Waypoint/Loiter를 설정하는 절차를 제공했으나 실제 비행에 성공한 Mission/ULog는 없다. 자동 Arming/Offboard 전환은 구현하지 않았다.
17. **통합 ROS Acceptance 범위**: 제공 smoke는 Mock start/stop/기본 zero-transmitter를 검증한다. 실제 dropout/실 링크/강제 process kill/복귀/serial 재연결은 추가 수동 acceptance가 필요하다. 순수 권한시험을 그 결과로 오인하지 않는다.
18. **모든 계측값 미측정**: Precision/Recall/mAP/FPS, 실제 RMSE, flight overshoot/settling, CPU/RAM, end-to-end latency는 결과가 없다. METHODS_AND_METRICS_KO.md 및 빈 metrics_template.csv로 측정한다.
