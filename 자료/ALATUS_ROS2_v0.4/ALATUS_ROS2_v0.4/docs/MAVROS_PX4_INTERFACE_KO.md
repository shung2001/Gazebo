# MAVROS / PX4 v1.17 Interface 검토

검토일: 2026-11-05. PX4 tag v1.17.0의 실제 commit은 d6f12ad1c4f70ad3230afd7d86e971421e02fef4다. 주석 tag object SHA a5eb12...와 commit SHA를 구분한다. Gazebo submodule gitlink는 b6127f4ec20de867e215fb5f78ae88b80f371909다. MAVROS ros2 branch 열람 SHA는 2d3f4db1101c7950c8817a9d788f0d11106fb261이며 사용자의 apt binary 버전과 동일하다고 가정하지 않는다.

## 지원성 단계

| 단계 | 근거 | 상태 |
|---|---|---|
| MAVLink 위치 메시지 | SET_POSITION_TARGET_LOCAL_NED | 소스 검토 PASS |
| MAVROS 송신 | setpoint_raw.cpp local_cb, PositionTarget | 소스 검토 PASS |
| PX4 수신 | mavlink_receiver.cpp handle_message_set_position_target_local_ned | 소스 검토 PASS |
| FW 소비 | FixedWingModeManager.cpp trajectory_setpoint position -> local/global reference -> POSITION | 소스 검토 PASS |
| 실제 apt Topic/Message | 사용자 설치 환경 필요 | NOT TESTED |
| Gazebo 비행 반응 | SITL 물리 시험 필요 | NOT TESTED |

문서는 고정익 위치 및 자세/추력 입력을 열거한다. v1.17 실제 FW 소스에는 Velocity/Acceleration 분기도 보이나 이 구현은 사용하지 않는다. 구버전 문서의 비표준 4096/8192/12288 type_mask를 일반 위치에 무조건 넣지 않는다. 선택한 tag 소스는 finite position으로 POSITION을 만든다. 기본 mask는 3576 (Vx/Vy/Vz/Ax/Ay/Az/Yaw/YawRate 무시), x/y/z만 유효다. 여기서 Takeoff/Land/Loiter special command를 만들지 않는다.

MAVROS /mavros/setpoint_raw/local의 형은 mavros_msgs/msg/PositionTarget이다. coordinate_frame enum은 FRAME_LOCAL_NED(1)이지만 ROS message.position은 ENU 값이다. MAVROS local_cb가 ENU -> NED 변환을 수행한다. 사용자 Publisher가 NED로 미리 바꾸지 않는다. Body Rate/Attitude path는 대안으로만 검토했으며 송신 구현하지 않았다. MAVSDK는 중복 송신 경로를 피하려고 도입하지 않았다.

## 상태 매핑

| MAVROS Topic | 타입 | 내부 필드/단위/유효성 |
|---|---|---|
| /mavros/state | mavros_msgs/State | connected, armed, mode, system_status; heartbeat 수신 age <=2.5 s |
| /mavros/local_position/pose | geometry_msgs/PoseStamped | ENU m, FLU->ENU xyzw; map frame, finite, norm, age<=0.5 s |
| /mavros/local_position/velocity_local | geometry_msgs/TwistStamped | ENU m/s; map frame, finite, age<=0.5 s |
| /mavros/imu/data | sensor_msgs/Imu | FLU rad/s; 선택 관측 |
| /mavros/vfr_hud | mavros_msgs/VfrHud | airspeed m/s; finite positive, age<=0.5 s |
| /mavros/global_position/raw/fix | sensor_msgs/NavSatFix | GPS status/lat/lon; 선택 관측 |
| /mavros/battery | sensor_msgs/BatteryState | percentage 0..1; 선택 관측 |

실제 배포에서 ros2 topic list -t/info -v/interface show로 표와 비교한다. Frame이 다르면 이름만 map으로 속이지 말고 설정/변환을 검토한다. Airspeed는 MAVLink 값의 물리적 유효성을 보증하지 못하므로 실제 sensor/estimate 및 PX4 ULog를 확인한다. Local altitude는 AGL이나 MSL이 아니다.

MAVROS State.manual_input은 Pilot가 제어권을 확보했다는 의미가 아니다. PX4 failsafe_flags 전체도 State 하나에서 나오지 않는다. 따라서 failsafe_known=false, manual_override_known=false를 유지한다. MAV_STATE CRITICAL/EMERGENCY 등은 affirmative fault로 차단하지만 ACTIVE라고 모든 Failsafe가 정상인 것은 아니다. Unknown을 true/정상으로 위조하지 않는다. Closed-loop SITL Permit은 이 한계를 명시적으로 검토해야 한다. RC mode switch를 실제로 시험하고 OFFBOARD 이탈을 감지하면 Sender를 revoke한다. 실기체 제어 승인은 제공하지 않는다.

## 권한과 중단

Shadow Launch에 Sender가 없다. 별도 Launch에서 Permit(enable/review flags/증거파일/실험 한계) + local SITL /proc executable + MAVROS Router fcu_urls 실제 파라미터가 전용 loopback URL과 일치해야 한다. 이것은 운용 가드이며 악의적 프로세스/위조된 링크를 막는 보안 attestation이 아니다. Serial Link에서는 거부한다.

/alatus/sitl_stream_enable true를 명시적으로 요청한 후 AUTO.LOITER에서 prestream하고 사용자가 OFFBOARD를 선택한다. 자동 Arm/Mode 변경은 없다. 명령/실상태/Track/Mission duplicate publishers, stale timestamp/steady receipt, 낮은 속도/범위 밖 자세·고도/target 상실을 차단한다. OFFBOARD를 본 이후 무효입력/Mode 이탈이면 restart 전까지 revoke한다. Stop은 마지막 목표를 계속 보내는 대신 Stream을 중단한다. 실제 비행 복귀는 PX4 COM_OF_LOSS_T와 COM_OBL_RC_ACT에 의존하므로 SITL에서 먼저 검증해야 한다.

PX4 요구사항의 >2 Hz, mode 진입 전 최소 1초 prestream을 고려해 20 Hz로 송신한다. 20 Hz Timer 생성이 실제 송신 주기/기체 응답 성공을 의미하지 않는다. Scheduler jitter/동기/Offboard loss를 측정해야 한다.
