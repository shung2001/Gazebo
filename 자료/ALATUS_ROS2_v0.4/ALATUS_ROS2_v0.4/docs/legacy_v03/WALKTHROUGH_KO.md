# 처음부터 실행하기

## 1. 실행 환경

이 ZIP의 ROS 실행 목표는 **Ubuntu 22.04 + ROS 2 Humble**입니다.
Windows PowerShell에서 ROS 명령을 실행하지 마십시오. Ubuntu PC 또는 설치가 완료된 Ubuntu 22.04 WSL2 터미널을 사용합니다.
WSL·외장 SSD 설치 및 기존 배포판 이동은 이 프로젝트에서 수행하지 않았습니다.

ROS가 없다면 [공식 Humble Ubuntu 설치 안내](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)를 먼저 완료합니다.
이후 아래 명령은 모두 Ubuntu bash에서 실행합니다. 작업 폴더는 Linux 홈 아래를 권장합니다.

```bash
lsb_release -ds
source /opt/ros/humble/setup.bash
printenv ROS_DISTRO
python3 --version
```

Ubuntu 22.04, humble, Python 3.10을 확인합니다. `source` 실패 시 진행하지 말고 설치를 확인합니다.
Humble 시스템 Python을 사용하십시오. pip로 rclpy를 설치하거나 임의 Python venv를 쓰지 않습니다.

```bash
sudo apt update
sudo apt install unzip python3-colcon-common-extensions python3-rosdep python3-pytest ros-humble-ros-base ros-humble-std-srvs ros-humble-launch-ros
```

rosdep을 처음 사용하는 PC에서만 `sudo rosdep init`을 실행합니다. 이미 초기화되었다면 반복하지 않습니다.
그다음 `rosdep update`를 실행합니다.

## 2. ZIP 풀기

ZIP을 Ubuntu 홈 폴더로 복사합니다. 실제 저장 위치가 다르면 아래 ZIP 경로를 바꿉니다.

```bash
mkdir -p ~/alatus_delivery
unzip ~/ALATUS_ROS2_STARTER.zip -d ~/alatus_delivery
cd ~/alatus_delivery/ALATUS_ROS2_STARTER
ls src
```

4개 패키지 폴더가 보여야 합니다. 이 디렉터리가 workspace root입니다.
이미 같은 폴더가 있으면 새 빈 디렉터리로 풀어서 버전이 섞이지 않도록 합니다.

## 3. ROS 없이 로직 테스트

```bash
python3 tools/run_local_tests.py
```

테스트가 실패하면 ROS 통합보다 먼저 원인을 수정합니다. 이는 ROS build 성공을 보장하지 않습니다.

## 4. 의존성 설치와 빌드

기본 workspace는 px4_msgs를 요구하지 않습니다. optional adapter는 명시적으로 실행하기 전까지 import하지 않습니다.

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep alatus
ros2 interface show alatus_interfaces/msg/GuidanceProposal
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

4개 패키지와 `GuidanceProposal` 필드가 보이는지 확인합니다.
빌드 실패 시 마지막 오류를 읽으십시오. `alatus_interfaces`를 찾지 못하면 workspace root 및 source 경로를 확인합니다.
기존 install을 source한 터미널에서 수정 후 rebuild 문제 발생 시 새 Ubuntu 터미널에서 Humble만 source하여 다시 빌드합니다.

## 5. 기본 시스템 시작 — 터미널 A

다른 팀/기체와 DDS가 섞이지 않도록 이 연습의 모든 터미널에 동일한 domain과 localhost 설정을 적용합니다.
이는 실제 제어 네트워크 보안 설정이 아닙니다. PX4 통합 때는 별도 네트워크 계획이 필요합니다.

```bash
cd ~/alatus_delivery/ALATUS_ROS2_STARTER
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=1
ros2 launch alatus_bringup shadow.launch.py
```

launch는 6개 노드를 시작합니다. PX4, Gazebo, 카메라, FC 연결은 필요 없습니다.
`use_sim_time` 기본값은 false입니다. mock 연습에서 true로 바꾸면 /clock이 없어 동작이 정지할 수 있습니다.

## 6. 통신과 상태 관찰 — 터미널 B

새 터미널마다 아래 준비를 반복합니다.

```bash
cd ~/alatus_delivery/ALATUS_ROS2_STARTER
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=1
ros2 node list
ros2 topic list -t
ros2 topic echo /alatus/mission_state --once
ros2 topic echo /alatus/safety_status --once
```

기대: mission은 IDLE, proposal_allowed=false; safety control_allowed=false.
topic이 보이지 않으면 터미널별 환경, domain, overlay source, launch 프로세스를 확인합니다.

## 7. 자동 ROS smoke 확인

새 기본 launch가 IDLE인 상태에서 터미널 B:

```bash
python3 tools/ros_smoke.py
```

이 도구는 메시지 3종 수신, 초기 IDLE/invalid proposal, shadow 시작, TRACK_SHADOW/valid proposal/inputs_valid를 확인합니다.
수신한 모든 SafetyStatus에서 control_allowed=false를 검사합니다. 종료 시 false 요청으로 초기화합니다.
성공 문구가 출력되어야 ROS mock smoke를 직접 통과한 것입니다. 제작 PC에서는 이 단계가 실행되지 않았습니다.

## 8. 직접 시작·고장 주입

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /alatus/mission_state --once
ros2 topic echo /alatus/guidance_proposal --once
ros2 param set /mock_perception dropout true
```

시작 후 약 1초 기다리면 TRACK_SHADOW, dropout 후 약 1초 기다리면 ABORT가 기대됩니다.
proposal.valid=false, control_allowed=false를 확인합니다.

```bash
ros2 param set /mock_perception dropout false
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

ABORT가 유지되고 true 요청이 거절되어야 합니다. 복구하려면:

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: false}'
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

tracker가 다시 확인된 뒤 TRACK_SHADOW로 돌아갑니다. 이 상태 전이는 비행 명령이 아닙니다.

## 9. 기록과 종료

선택적으로 `sudo apt install ros-humble-rosbag2` 후 새 터미널에서:

```bash
ros2 bag record /alatus/detection /alatus/target_track /alatus/aircraft_status /alatus/mission_state /alatus/guidance_proposal /alatus/safety_status
```

실행 중단은 각 터미널에서 Ctrl+C. bag 재생은 별도 연습 세션에서 수행하십시오.
이 로직은 오래된 timestamp를 거절하므로 현재 wall clock에서 과거 bag를 재생하면 valid=false가 정상입니다.
재생 시간/관측 시간 정책을 정하기 전에는 재생 결과를 실시간 정상 동작과 동일시하지 않습니다.

## 10. 다음 단계

TEAM.md의 담당별 수정 후 로직 테스트 → colcon build/test → ROS smoke → dropout 확인 순으로 통합합니다.
PX4 상태 수신은 PX4_INTEGRATION.md를 별도로 따릅니다. 기본 mock launch와 동시에 상태 publisher를 실행하지 마십시오.
실제 비행 제어가 필요하면 별도 설계·검토·SITL 검증 프로젝트가 필요합니다. 이 ZIP에는 제어 활성화 단계가 없습니다.
