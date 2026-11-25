# 05. PX4 v1.17 / Gazebo / MAVROS

## 1. 이번 단계의 목적

공식 고정익 모델의 실제 비행과 상태 수신을 확인한다. 모델 표시만으로 성공 처리하지 않는다.

## 2. 필요한 사전조건

기존 ~/PX4-Autopilot v1.16은 유지. 새 경로에 충분한 디스크, 개발 PC 그래픽 환경, 네트워크가 필요하다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
bash tools/fetch_px4_v117.sh
cd ~/PX4-Autopilot-v1.17.0
git rev-parse HEAD
git submodule status --recursive
bash Tools/setup/ubuntu.sh
```

설치 안내에 따라 로그아웃/재부팅한 뒤 새 터미널:

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
bash tools/run_sitl_v117.sh baseline
```

기대 make target은 make px4_sitl gz_advanced_plane이다. PX4 콘솔에서:

```text
commander status
listener vehicle_status
listener vehicle_local_position
listener vehicle_attitude
mavlink status
```

QGroundControl을 별도 실행한다. Mission 화면에서 Takeoff → 안전한 고도/경로 Waypoint → Loiter를 구성해 Upload하고, SITL임을 확인한 뒤 화면에서 Arm/Start한다. 이 문서가 실제 실행한 Mission 파일을 제공하는 것은 아니다. takeoff 가능 조건, 활주/런치 로직과 실패 경고를 먼저 해결하고 기본 비행 로그를 남긴다. ALATUS 발사관/날개 전개는 이 모델에 구현하지 않았다.

별도 터미널, Camera 없이도 시각을 맞추기 위한 /clock Bridge:

```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
```

Gazebo/Humble Bridge 설치는 06을 참고한다. 다른 터미널에서:

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
bash tools/run_mavros_sitl.sh
```

Bridge 터미널도 같은 ROS_DOMAIN_ID를 사용해야 한다. 기본 예제와 일치시키려면 Bridge 실행 전 export를 적용한다.

```bash
ros2 topic list -t
ros2 topic info /mavros/local_position/pose -v
ros2 topic echo /mavros/state --once
ros2 topic echo /mavros/local_position/pose --qos-reliability best_effort --once
ros2 topic echo /mavros/vfr_hud --once
ros2 interface show mavros_msgs/msg/PositionTarget
dpkg-query -W 'ros-humble-mavros*'
```

source/export는 각 터미널에서 반복한다. ALATUS Shadow 연결:

```bash
ros2 launch alatus_bringup sitl_shadow.launch.py
```

## 5. 전체 코드 또는 수정파일

fetch_px4_v117.sh는 기존 디렉터리가 있으면 중단한다. run_sitl_v117.sh는 commit을 검사한다. 공식 모델의 질량/공력 값을 ALATUS 값으로 옮기지 않는다. pinned Advanced Plane에는 AdvancedLiftDrag, AirSpeed, Motor Model, Servo joints 및 센서가 포함되어 있음을 소스에서 확인했다.

## 6. 예상 출력

commit=d6f12ad1c4f70ad3230afd7d86e971421e02fef4. QGC 연결, Sensor 갱신, 실제 위치/속도/고도/선회 변화가 관찰되어야 한다. MAVROS connected=true와 유효 Pose/Velocity/Airspeed가 필요하다.

## 7. 성공 판정

QGC/ULog와 상태 Topic으로 Arm, Takeoff, 비행, 고도/선회 변화의 증거를 남겼을 때만 기본 비행 PASS로 기록한다. 현재 제공자 환경에서는 NOT TESTED다.

## 8. 대표적인 오류

PX4 instance 0 already running, gz_bridge 빌드 실패, QGC GLIBC 오류, MAVROS UDP disconnected.

## 9. 오류 해결 방법

기존 PX4 터미널에서 Ctrl+C로 종료한 뒤 해당 프로세스만 확인한다. v1.16과 v1.17을 동시에 instance0으로 켜지 않는다. 첫 compile error와 설치된 Harmonic 버전을 확인한다. Ubuntu 22.04와 호환되는 QGC binary를 사용한다. MAVROS의 14540/14557와 PX4 mavlink status를 비교하고, Topic이 보여도 실제 PX4 command 소비 성공으로 간주하지 않는다.

## 10. 다음 단계와 연결

기본 비행이 확보되면 06에서 Camera/Target을 추가한다.
