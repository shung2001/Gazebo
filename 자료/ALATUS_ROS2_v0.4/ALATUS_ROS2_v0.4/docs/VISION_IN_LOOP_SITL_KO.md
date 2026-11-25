# 06. Vision-in-the-loop / Closed-loop SITL

## 1. 이번 단계의 목적

Gazebo의 실제 렌더 영상을 추론하고 물리 경로 응답을 별도 단계로 검증한다.

## 2. 필요한 사전조건

05 기본 비행 PASS, 실제 모델, Calibration, 검토한 Guidance config. 이 단계는 제공자 환경 NOT TESTED다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

Humble 기본 ros_gz는 Fortress 조합이다. Harmonic과 혼용하지 않는다. 공식 Gazebo의 Humble/Harmonic 지침에 따라 OSRF 저장소를 준비한다(PX4 setup에서 이미 준비했을 수 있음):

```bash
sudo apt update
sudo apt install -y curl lsb-release gnupg
sudo curl -fL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt update
sudo apt install -y gz-harmonic ros-humble-ros-gzharmonic
```

APT에서 ros-humble-ros-gz* 충돌/삭제 제안이 나오면 설치 계획을 읽고 Fortress 기반 다른 프로젝트 영향을 검토한다. 무조건 -y로 기존 프로젝트 패키지를 제거하지 않는다.

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
python3 tools/install_sim_assets.py --px4 ~/PX4-Autopilot-v1.17.0
bash tools/run_sitl_v117.sh vision
```

별도 터미널, 공통 source/export 후:

```bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
bash tools/bridge_camera.sh
```

Gazebo Transport/ROS 입력을 확인:

```bash
gz topic -l
ros2 topic hz /alatus/camera/image
ros2 topic echo /alatus/camera/image --field header --once
ros2 run rqt_image_view rqt_image_view
```

rqt_image_view가 없으면 sudo apt install ros-humble-rqt-image-view. frame_id는 camera_optical이어야 한다. 다른 값이면 Sensor 설정/Bridge 결과를 확인한 뒤 실제 optical frame에 맞추며 Body Frame을 Optical인 것처럼 이름만 바꾸지 않는다.

03/04에서 준비한 config와 venv로 실행:

```bash
bash tools/run_mavros_sitl.sh
# 위 명령은 별도 터미널에서 유지
ros2 launch alatus_bringup vision_sitl_shadow.launch.py config_path:="$PWD/config/vision_sitl_local.yaml" perception_prefix:="$PWD/.venv/bin/python3"
```

다른 터미널:

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /alatus/visual_command --once
bash tools/record_metrics.sh log/vision-sitl-shadow
```

Closed-loop는 다음 검토를 모두 끝낸 뒤에만 실행한다. 기존 Shadow Launch는 종료한다. PX4는 비행 중 AUTO.LOITER 상태로 유지한다.

```bash
cp config/sitl_permit.example.json config/sitl_permit.local.json
code config/sitl_permit.local.json
```

Permit의 enable/review flags, PX4 commit, 설치 MAVROS version, 실제 evidence_paths, 검토한 속도/고도/자세/거리 한계를 입력한다. example 그대로는 반드시 시작 실패한다. 해당 한계의 실기체 값은 제공하지 않는다. 실제 PX4 SITL PID를 다음 목록에서 직접 확인한다:

```bash
ps -eo pid,args | rg 'px4_sitl_default/bin/px4'
```

아래 12345를 확인한 PID로 교체한다:

```bash
ros2 launch alatus_bringup sitl_closed_loop.launch.py config_path:="$PWD/config/vision_sitl_local.yaml" perception_prefix:="$PWD/.venv/bin/python3" permit_path:="$PWD/config/sitl_permit.local.json" sitl_pid:=12345
```

다른 터미널:

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 service call /alatus/sitl_stream_enable std_srvs/srv/SetBool '{data: true}'
ros2 topic hz /mavros/setpoint_raw/local
ros2 topic echo /alatus/sitl_authority --once
```

PX4가 유효한 위치 Setpoint stream을 최소 1초 이상 수신한 것을 확인한 후, QGC 또는 PX4 SITL 콘솔에서 사용자가 명시적으로 Offboard를 선택한다:

```text
commander mode offboard
listener trajectory_setpoint
```

송신 Stop:

```bash
ros2 service call /alatus/sitl_stream_enable std_srvs/srv/SetBool '{data: false}'
```

실험 전에 COM_OF_LOSS_T/COM_OBL_RC_ACT와 mode switch 복귀를 확인한다. Stream 중단, Target Lost, Camera 정지, MAVROS 손실 시 실제 선택한 PX4 복귀를 관찰한다.

## 5. 전체 코드 또는 수정파일

sim/alatus_recovery.sdf는 실험용 4 m Target을 ENU (200,0,30)에 둔다. sim/camera_sensor.sdf와 install_sim_assets.py는 원본 Advanced Plane을 별도 advanced_plane_vision 모델로 복사해 Camera만 추가한다. Net 포획 충돌/감속은 구현하지 않았다. run script는 4008 airframe과 새 모델을 연결한다. 원본 Advanced Plane SDF는 수정하지 않는다.

## 6. 예상 출력

실제 영상 Topic에 과녁이 보이고 모델이 검출해야 한다. 단지 YOLO 노드가 켜진 상태는 PASS가 아니다. 현재 위치의 과녁이 비행 FOV 밖이면 No Detection이 정상이며 QGC에서 접근경로를 먼저 설정한다. Synthetic ring과 학습 이미지 Domain Gap으로 미검출될 수 있다.

## 7. 성공 판정

Stage A: 기본 비행 + Mock 상태연동/Guidance. Stage B: 실제 Camera→YOLO→KF→Guidance. Closed-loop: Setpoint 수신 + OFFBOARD 진입 + 기체 궤적 변화 + Loss/Mode 복귀를 각각 독립 증거로 확인한다. 현재 모두 NOT TESTED이며 Model/Geometry 미제공 부분은 BLOCKED다.

## 8. 대표적인 오류

Bridge가 설치되어도 영상 없음, frame mismatch, Target 미검출, Permit incomplete, /mavros_router 조회 불가, Offboard 진입 거부.

## 9. 오류 해결 방법

gz topic -l로 실제 Camera topic부터 확인한다. Sensor/Rendering plugin 및 headless GPU 설정을 점검한다. 모델 식별/해상도/Class를 확인하며 Domain Gap을 별도 보고한다. ROS_DOMAIN_ID와 /clock, MAVROS use_sim_time을 일치시킨다. PX4 local reference/GPS가 유효한지 listener로 확인한다. 설치 MAVROS가 Router parameter API를 제공하지 않으면 Sender는 fail-closed이므로 해당 버전을 검토해 Adapter를 수정해야 한다.

## 10. 다음 단계와 연결

통합 결과가 확보되어도 Onboard Control을 열지 않는다. 07에서 공통 알고리즘을 읽기 전용으로 이식한다.
