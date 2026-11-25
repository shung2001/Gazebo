# 07. Raspberry Pi 5 Onboard Shadow

## 1. 이번 단계의 목적

동일 추정·유도 코드를 ARM64 Docker에서 재사용하고 실제 Hailo/Camera 결과만 입력받는다.

## 2. 필요한 사전조건

Pi OS 64-bit, Pi5, Hailo-8 26 TOPS, Camera Module 3. 카메라와 Hailo의 실제 SDK 파이프라인이 별도로 동작해야 한다.

## 3. 실행환경

Host: Raspberry Pi OS ARM64. Container: Ubuntu 22.04 ARM64 / ROS2 Humble. 모델 Compiler는 지원되는 별도 개발환경에서 수행한다.

## 4. 실제 실행 명령어

Host 조사:

```bash
uname -a
uname -m
cat /etc/os-release
rpicam-hello --list-cameras
hailortcli --version
hailortcli scan
hailortcli fw-control identify
dpkg-query -W '*hailo*'
```

명령이 없으면 해당 도구가 설치되지 않은 것이다. 장치와 패키지를 먼저 식별하고 Raspberry Pi/Hailo 공식 Hailo-8 지원 절차를 적용한다. 최신 master를 무조건 설치하지 않는다. Docker가 없으면 Pi OS 공식 Docker Engine 설치 지침으로 준비하고 docker version/compose version을 확인한다.

```bash
cd ~/ALATUS_ROS2_v0.4
mkdir -p deploy/runtime deploy/data
sudo chown 10001:10001 deploy/runtime deploy/data
docker compose -f deploy/compose.v04.yaml build
docker compose -f deploy/compose.v04.yaml up
```

Host Hailo callback의 실제 결과를 연결하는 기존 API:

```python
from integration.hailo_result_client import ResultClient
client = ResultClient('/absolute/project/deploy/runtime/perception.sock')
# 아래 값은 실제 capture/exposure timestamp와 실제 detector 결과에서 가져와야 한다.
# client.send(capture_stamp_ns, width, height, detections, frame_id='camera_optical')
# detections entry: class_id string, confidence float, stable unique track_id,
# bbox_xywh_px=[left,top,width,height] in ORIGINAL IMAGE pixels.
```

실제 SDK가 없어 위 send에 가짜 결과를 넣는 실행 예제는 제공하지 않는다. Host class명은 config/onboard_shadow.yaml의 hailo_class_name으로 지정한다. 같은 host system-clock ns로 exposure 시각을 매핑해야 한다.

Pixhawk TELEM Device/Baud를 먼저 확정한 뒤 Container에서 상태 MAVROS를 따로 실행한다. Serial 공유를 위해 compose의 devices 항목과 group_add에 실제 device와 dialout group ID를 명시적으로 추가한다. 기본 파일은 장치를 추정해 열지 않는다. Host에서 Device를 확인:

```bash
ls -l /dev/serial/by-id
getent group dialout
```

수정 후 Container에서:

```bash
docker compose -f deploy/compose.v04.yaml exec observer bash
export ALATUS_FCU_URL='TBD_CONFIRMED_DEVICE:BAUD'
bash tools/run_mavros_onboard.sh
```

TBD 문자열을 그대로 실행하지 않는다. 확인한 실제 값만 넣는다. GeographicLib datasets가 필요한 MAVROS 설정이면 Docker에 설치하고 재빌드한다. 실제 GPIO/TELEM 전압·공통접지·PX4 MAVLink 포트 설정도 하드웨어 자료로 확인한다.

다른 Container 터미널:

```bash
source /opt/ros/humble/setup.bash
source /opt/alatus/install/setup.bash
ros2 topic echo /alatus/aircraft_state --once
ros2 topic echo /alatus/track_estimate --once
ros2 topic echo /alatus/safety_status --once
docker stats
```

마지막 docker stats는 Host 터미널에서 실행한다. CPU/RAM/온도/전체 capture-to-guidance 지연은 별도 기록한다.

## 5. 전체 코드 또는 수정파일

deploy/Dockerfile.v04, compose.v04.yaml, entrypoint.sh, config/onboard_shadow.yaml, integration/hailo_result_client.py. Hailo/Camera는 Host에서 실행하고 Unix Datagram만 mount하므로 컨테이너에 전체 /dev나 privileged를 기본 부여하지 않는다.

## 6. 예상 출력

실입력이 없으면 Invalid/IDLE 또는 입력 대기가 정상이다. Onboard Shadow는 Sender를 실행하지 않으며 control_allowed=false다. 모델이 작동하지 않는데 MOCK을 섞어 성공 처리하지 않는다.

## 7. 성공 판정

실제 Camera exposure/HEF inference 결과, MAVROS serial 상태, 유효 Track, 검토 후 Guidance 계산과 CPU/RAM/지연을 모두 기록해야 Level 5다. 현재 NOT TESTED/BLOCKED다.

## 8. 대표적인 오류

ARM64 의존 패키지 없음, Socket 권한 거부, Hailo HEF architecture mismatch, UART 권한/baud 오류.

## 9. 오류 해결 방법

컨테이너 platform과 실제 uname -m을 확인한다. UID/GID와 socket mount를 맞춘다. Hailo Driver/HailoRT/DFC/Model Zoo/HEF target을 함께 고정한다. Serial device를 host에서 중복 사용하지 않는다. ROS use_sim_time=false와 host system clock 동기를 확인한다. SDK 미확보 상태에서 API 이름을 추정해 변경하지 않는다.

## 10. 다음 단계와 연결

온보드 상태관측/Shadow 결과를 별도 검토한다. 실비행 제어는 v0.4 완료 범위가 아니다.
