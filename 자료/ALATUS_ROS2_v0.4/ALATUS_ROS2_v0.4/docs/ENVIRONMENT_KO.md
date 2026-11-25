# 02. Ubuntu / ROS 2 / MAVROS 설정

## 1. 이번 단계의 목적

Custom Message와 새 패키지를 실제 Humble에서 빌드한다.

## 2. 필요한 사전조건

Ubuntu 22.04 네이티브 PC, 인터넷, sudo. 기존 Humble이 있으면 재설치하지 않는다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

확인:

```bash
lsb_release -ds
/usr/bin/python3 --version
test -f /opt/ros/humble/setup.bash && echo HUMBLE_PRESENT
```

Humble이 없는 새 PC에서만 공식 ROS apt-source 설정을 한다:

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl ca-certificates
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
ROS_APT_SOURCE_VERSION=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')
curl -fL -o /tmp/alatus-ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo dpkg -i /tmp/alatus-ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-humble-desktop
```

전체 PC 공통:

```bash
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-pytest python3-numpy python3-yaml python3-opencv python3-venv ros-humble-mavros ros-humble-mavros-extras ros-humble-cv-bridge ros-humble-std-srvs ros-humble-launch-ros ros-humble-rosidl-default-generators
sudo /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh
# /etc/ros/rosdep/sources.list.d/20-default.list가 없는 최초 설치에서만 실행
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then sudo rosdep init; fi
rosdep update
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
ros2 interface show alatus_interfaces/msg/TrackEstimate
python3 -c 'from alatus_interfaces.msg import MissionState,VisualCommand; print(MissionState,VisualCommand)'
bash tools/validate_humble_v04.sh
```

검증 스크립트는 시험 후 Launch를 종료한다. 계속 관찰하려면 새로 실행:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
ros2 launch alatus_bringup mock_shadow.launch.py
```

다른 터미널에도 반드시 같은 두 source 및 export를 적용:

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
ros2 topic echo /alatus/track_estimate --once
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /alatus/visual_command --once
ros2 topic echo /alatus/safety_status --once
```

## 5. 전체 코드 또는 수정파일

실행 스크립트 전체: tools/validate_humble_v04.sh, tools/ros_v04_smoke.py. 패키지 manifest/setup/CMake와 msg 파일은 src 각 패키지에 있다. 이 문서의 예상 결과는 제공자 ROS 런타임 실측이 아니다.

## 6. 예상 출력

colcon에 ALATUS 패키지 5개가 보이고 메시지 Python import가 성공한다. Mock에서 track.valid=true, Mission 요청 후 visual_command.valid=true, safety_status.control_allowed=false. 실제 숫자/시각은 실행마다 달라진다.

## 7. 성공 판정

빌드, colcon test, 신규/회귀시험, ROS acceptance 모두 성공하고 /mavros/setpoint_raw/local publisher가 0개다.

## 8. 대표적인 오류

Signed-By 충돌, MissionState is invalid, 노드 중복 이름, package not found.

## 9. 오류 해결 방법

APT 충돌은 sources.list.d의 ros2.list와 ros2.sources 중복을 먼저 확인한다. 기존 정상 패키지 방식에 맞게 한 정의만 유지하며 무조건 key를 삭제하지 않는다. 메시지 오류는 echo 터미널에서 source install/setup.bash와 Python import를 재확인한다. 빌드 에러의 첫 줄과 install 경로를 확인한 뒤 필요한 패키지만 재빌드한다. 노드 중복이면 ps로 실제 Launch 수와 topic publisher count를 비교한다. CLI graph만 보고 프로세스를 무작위 종료하지 않는다.

```bash
ros2 pkg prefix alatus_interfaces
ros2 topic info /alatus/mission_state -v
ros2 node list
```

## 10. 다음 단계와 연결

ROS acceptance가 통과하면 Level 2 Mock에 대한 증거를 보관한다. Replay는 별도 모델을 확보해 03으로 진행한다.
