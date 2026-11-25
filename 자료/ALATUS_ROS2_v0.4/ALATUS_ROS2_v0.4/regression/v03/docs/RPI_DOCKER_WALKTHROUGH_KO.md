# Raspberry Pi Ubuntu Docker + ROS 2 관찰 시스템 v0.3

이 문서가 이전 v0.1/v0.2 실행 설명보다 우선합니다.
**실기체 탑재를 위한 소스·배포 구성**이며 실비행 검증이 완료된 제어 소프트웨어는 아닙니다.
제작 환경에는 Docker, ROS 2, Raspberry Pi, Hailo가 없어 이 환경들의 build/run/hardware 시험은 수행하지 못했습니다.

## 1. 구현한 범위

* 기존 v0.2 제안 파라미터 47개를 포함한 application parameter를 구현했습니다.
* parameter_specs.py는 선언할 타입·기본값·범위·설명·read_only 정책의 실행 원본입니다.
* parameters.py는 타입·유한수·범위·결합 조건을 검사합니다. ros_parameters.py가 실제 Humble 선언과 descriptor/callback을 연결합니다.
* startup-only 파라미터 변경은 거절합니다. dropout만 실행 중 변경합니다.
* tracking 확인 횟수/confidence/gap/age, 노드 주기, 입력별 age, 영상 중심/gain/limit, source 검사, mock 상태 주입이 실제 로직에 연결됩니다.
* 관측 미래값이 accepted timestamp를 오염시키는 문제와 stale track 카운트 표시를 수정했습니다.
* 상태 source 문자열과 단일 publisher를 검사합니다. 탐지 토픽도 단일 publisher를 확인합니다.
* steady timer/receipt gap, ROS clock 역행·sim freeze 검사를 추가했습니다. clock fault는 재시작 전까지 유지합니다.
* **제어 송신 없음, control_allowed=false, mission 자동 시작 없음**은 유지합니다.

현재 구현은 자세/위치/속도/airspeed 기반 실제 guidance, RC 개입 판단, PX4 command, 공력 envelope, 비행 watchdog을 제공하지 않습니다.
발행 source 이름 검사는 인증이 아니며 외부 노드의 명령 송신까지 막지 않습니다.

## 2. 권장 배치 구조와 미확인 항목

```text
64-bit Linux 호스트 (정확한 OS/커널/보드 확인 필요)
 ├─ 카메라 + 호환 Hailo runtime + 실제 추론/추적 pipeline [사용자가 선택·검증]
 │    └─ ResultClient hook → Unix datagram /run/alatus/perception.sock
 ├─ PX4 uXRCE-DDS Agent [별도 설치·검증]
 └─ Ubuntu 22.04 / Humble Docker [이번 소스]
      perception_socket → tracker → mission → guidance → safety_gate
      PX4 VehicleStatus → optional px4_status ───────────────┘
```

Hailo 사용이 미정이므로 ROS 컨테이너에 Hailo SDK·카메라 드라이버를 임의로 설치하지 않았습니다.
호스트에서 추론하고 결과만 전달하면 호스트 Python ABI와 Ubuntu Python 3.10을 분리할 수 있습니다.
AI HAT 세대, HailoRT/driver/firmware/HEF, camera preprocessing/postprocessing은 실제 조합을 받은 뒤 고정해야 합니다.
현재 Raspberry Pi 공식 AI 안내는 Raspberry Pi 5와 64-bit Raspberry Pi OS를 기준으로 합니다.
Ubuntu 컨테이너가 호스트 커널/PCIe 드라이버를 대신 제공하는 것은 아닙니다.
[Raspberry Pi 공식 AI 안내](https://www.raspberrypi.com/documentation/computers/ai.html)

HailoRT 공식 저장소는 Hailo-8 계열과 Hailo-10/15 계열의 branch 구분을 명시합니다.
따라서 'Hailo니까 master/latest 설치'는 이 프로젝트의 절차가 아닙니다.
[HailoRT 공식 README](https://github.com/hailo-ai/hailort)

## 3. 탑재 전 확인할 정보

확정 정보: Raspberry Pi 5 / 8GB RAM, Raspberry Pi OS(사용자 표현 Raspbian), Hailo-8 26 TOPS, Camera Module 3.
호스트 OS의 정확한 release/64-bit 여부, uname -m, 커널, Docker/Compose 버전, HailoRT/driver 버전,
camera 장치/해상도/노출 시각, HEF target architecture/입출력/NMS, stable track ID,
PX4 tag/hash/board/transport/Agent/msg SHA, 전원·냉각·저장장치·리소스 예산을 기록합니다.
자료가 없으면 Hailo 인식 및 PX4 integration 완료로 표시하지 않습니다.

## 4. Raspberry Pi에 소스 준비

이후 명령은 Raspberry Pi의 **Linux bash**입니다. Windows PowerShell 명령이 아닙니다.
Docker Engine과 Compose plugin은 사용하는 호스트 OS의 공식 설치 안내에 따라 먼저 준비합니다.
이 절차는 Docker를 새로 설치하거나 기존 호스트 설정을 변경하지 않습니다.

```bash
uname -m
cat /etc/os-release
docker version
docker compose version
```

호스트는 aarch64/arm64를 기대합니다. 32-bit armv7이면 진행하지 말고 OS/보드 구성을 확인합니다.
ZIP을 Pi 홈 폴더에 복사하고 새 빈 폴더에 압축을 풉니다.

```bash
mkdir -p ~/alatus-v03
unzip ~/ALATUS_ROS2_ONBOARD_v0.3.zip -d ~/alatus-v03
cd ~/alatus-v03/ALATUS_ROS2_STARTER
```

이제 아래 작업의 기준 경로는 이 workspace root입니다.

## 5. 파라미터를 적용하는 법

Mock: src/alatus_bringup/config/shadow.yaml
탑재 관찰: deploy/onboard.yaml (컨테이너 /etc/alatus/onboard.yaml에 read-only mount)

예: tracker.confirm_hits를 5로 바꾸려면:

```yaml
tracker:
  ros__parameters:
    confirm_hits: 5
```

실제 파일의 tracker 섹션에서 해당 값만 수정합니다. 위 조각으로 파일 전체를 덮어쓰지 않습니다.
변경 후 전체 launch/container를 재시작합니다. runtime set은 read_only로 거절됩니다.
float는 10.0처럼 float로 씁니다. bool 대신 문자열 "false"를 쓰지 않습니다.
centre±amplitude 범위와 timer/age 관계가 틀리면 시작 실패가 의도된 동작입니다.
onboard 기대 source는 PX4_VEHICLE_STATUS_ONLY이며 mock 값을 섞지 않습니다.

## 6. image 빌드와 기본 관찰 실행

현재 Dockerfile은 ros:humble-ros-base-jammy를 사용합니다.
공식 image manifest에는 Jammy와 arm64v8이 명시되어 있습니다.
운영용으로 보관할 때는 시험한 image digest와 최종 image ID도 기록하십시오. tag는 이동할 수 있습니다.
[공식 ROS image manifest](https://github.com/docker-library/official-images/blob/master/library/ros)

```bash
mkdir -p deploy/runtime deploy/data
sudo chown "10001:$(id -g)" deploy/runtime
sudo chmod 2770 deploy/runtime
sudo chown 10001:10001 deploy/data
sudo chmod 0770 deploy/data
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml build
docker compose -f deploy/compose.yaml up -d
docker compose -f deploy/compose.yaml logs --tail=100 observer
```

Compose 파일 기준 상대 경로는 deploy 디렉터리입니다.
컨테이너 사용자는 UID/GID10001입니다. 소유권 변경 대상은 위 두 폴더에 한정합니다.
runtime 폴더는 현재 호스트 사용자의 group과 setgid를 사용하여 새 socket이 같은 group을 상속하게 합니다. Hailo sender가 다른 사용자라면 별도 공용 group을 구성하고 해당 폴더/socket 접근권한을 확인하십시오.
권한 문제를 privileged=true나 chmod777로 해결하지 않습니다.

기본 실행은 **PX4 adapter disabled**, perception socket 대기, mission=IDLE입니다.
mock_status/mock_perception은 올라오지 않습니다. 외부 데이터가 없으므로 inputs_valid=false가 정상입니다.
healthcheck는 일부 핵심 노드와 새 diagnostic 수신만 검사합니다. camera/Hailo/PX4의 정상 상태나 비행 허가가 아닙니다.
unhealthy만으로 Docker가 재시작하는 설정은 아닙니다. restart는 의도적으로 no입니다.

## 7. 컨테이너 안에서 확인

```bash
docker compose -f deploy/compose.yaml exec observer /usr/local/bin/alatus-entrypoint ros2 node list
docker compose -f deploy/compose.yaml exec observer /usr/local/bin/alatus-entrypoint ros2 param get /tracker confirm_hits
docker compose -f deploy/compose.yaml exec observer /usr/local/bin/alatus-entrypoint ros2 topic echo /alatus/safety_status --once
```

confirm_hits는 실제 설정값, control_allowed는 false여야 합니다.
잘못된 YAML로 노드가 종료되면 onboard launch는 전체 observer를 종료하도록 구성했습니다.
이 동작은 프로세스 감독이며 PX4 안전장치를 대신하지 않습니다.

## 8. Mock/ROS parameter acceptance를 별도 컨테이너에서 수행

onboard observer와 분리된 시험입니다. 실행 중 서비스를 먼저 내립니다.

```bash
docker compose -f deploy/compose.yaml down
docker run --rm --user 0:0 --network host --entrypoint /usr/local/bin/alatus-entrypoint alatus-observer:0.3.0 bash tools/validate_humble.sh
```

이 시험용 container만 root와 일반 writable layer를 사용해 image 안의 build 폴더에 기록합니다. 실제 observer 서비스는 UID10001/read_only로 유지합니다. ROS build/test와 실제 parameter service/smoke를 수행합니다.
read_only descriptor, clock runtime 변경 거절, dropout 변경, 잘못된 시작값 거절을 검사합니다.
결과를 직접 확인하기 전에는 ROS API 시험 PASS라고 기록하지 않습니다.
위 과정이 끝난 뒤 `docker compose ... up -d`로 onboard 관찰 구성을 다시 시작합니다.

## 9. PX4 상태 수신 활성화 — 버전 변경을 위한 profile

2026-11-02 조회에서 공식 latest stable 릴리스는 v1.17.0이었습니다.
이는 자동 업데이트 지시가 아닙니다. 최종 설치 시 다시 확인하고 시험한 commit을 고정하십시오.
[공식 v1.17.0 릴리스](https://github.com/PX4/PX4-Autopilot/releases/tag/v1.17.0)

release/1.17의 VehicleStatus 정의는 MESSAGE_VERSION=1이며 이 adapter가 소비하는 기본 필드가 있습니다.
하지만 그 사실만으로 기체 연결이 검증되지는 않았습니다.
[공식 release/1.17 정의](https://raw.githubusercontent.com/PX4/px4_msgs/release/1.17/msg/VehicleStatus.msg)

deploy/px4_profile.json은 **검토 미완료 template**입니다. profile 없이 임의 버전을 자동 허용하지 않습니다.
다음 항목을 실제 자료로 확인하고 deploy/onboard.yaml과 profile에 같은 값을 기록합니다.

1. 정확한 firmware_tag 및 firmware_commit_sha.
2. 해당 firmware와 대조한 px4_msgs_ref 및 px4_msgs_commit_sha.
3. expected_message_version, VehicleStatus 필드 type, ARMING_STATE_ARMED 상수.
4. 해당 px4_msgs commit의 msg/VehicleStatus.msg 파일 bytes에 대한 SHA256.
5. 실제 DDS namespace/status_topic, Agent/QoS/time-sync 설정.

PX4 source 및 px4_msgs clone에서 hash는 `git rev-parse HEAD`, 메시지 파일 hash는
`sha256sum msg/VehicleStatus.msg`로 기록합니다. 커밋 SHA와 파일 SHA256은 다른 값입니다.

onboard.yaml의 contract_profile_path는 컨테이너 /etc/alatus/px4-profile.json입니다.
Compose가 deploy/px4_profile.json을 read-only로 mount합니다.
검토 완료 후에만 profile.reviewed=true와 config.contract_reviewed=true를 지정합니다.
profile의 firmware_tag/ref/SHA/version과 노드 설정이 정확히 같아야 합니다.
adapter는 설치된 VehicleStatus.msg의 SHA256, generated class field type/version/arming 상수도 검사합니다.

그다음 빌드할 실제 px4_msgs commit을 지정합니다.

```bash
export PX4_MSGS_SHA='여기에_검토한_실제_40자리_SHA'
```

위 placeholder는 실제 SHA로 바꿔야 합니다. Dockerfile은 지정 commit을 checkout하고 build provenance 파일에 기록합니다.
이 값이 비어 있으면 image에 px4_msgs가 없으며 adapter 활성화는 실패합니다.

```bash
docker compose -f deploy/compose.yaml build
export ENABLE_PX4_STATUS=true
docker compose -f deploy/compose.yaml up -d --force-recreate
```

firmware를 바꿀 때는 profile 검토·기록과 msg image rebuild, 실제 telemetry 시험을 반복합니다.
동일한 field type이 유지되면 mapping 코드를 유지할 수 있지만 field type/enum 의미가 바뀌면 코드도 다시 검토해야 합니다.
profile 값만 고치는 것으로 실제 호환성 시험을 생략하지 않습니다. RC/failsafe/nav_state의 의미도 해당 firmware 정의로 확인합니다.

network_mode=host는 Linux 기준이며 serial device를 ROS container에 직접 전달하지 않습니다.
별도 Agent가 호스트에서 PX4와 연결하도록 구성합니다. 이 image가 Agent를 설치/실행하지 않습니다.
ROS_DOMAIN_ID를 Client/Agent와 맞춥니다. ROS_LOCALHOST_ONLY=1은 같은 호스트 Agent 관찰용입니다.
PX4가 failsafe이면 Mission 시작 후 ABORT가 정상일 수 있습니다. 이를 숨기려고 Mock 상태를 추가하지 않습니다.
실제 firmware SHA를 장치에서 자동 검증하는 기능은 없으며 profile은 선언·설치 메시지 검사이지 wire 통합 증명이 아닙니다.

## 10. Hailo 결과 연결 — 실제 추론 pipeline 준비 후

integration/hailo_result_client.py는 **추론 결과 전달 hook**이며 Hailo 추론 엔진이 아닙니다.
HEF 모델·전처리·출력/NMS·tracker를 확인하지 못했으므로 특정 Hailo API를 임의로 호출하지 않습니다.
실제로 동작하는 vendor pipeline callback에서 다음 계약으로 전달하도록 연결합니다.

```python
from hailo_result_client import ResultClient

client = ResultClient('/실제/호스트경로/deploy/runtime/perception.sock')
# 아래 함수는 예시 연결점입니다. pipeline API 이름이 아닙니다.
def forward_verified_result(exposure_system_time_ns, width, height, tracked_objects):
    return client.send(exposure_system_time_ns, width, height, tracked_objects)
```

tracked_objects 항목의 형식:

```json
{"class_id":"target","confidence":0.95,"track_id":7,"bbox_xywh_px":[100,120,40,60]}
```

* class_id는 실제 model의 class map에 맞추고 deploy/onboard.yaml의 target_class_id도 일치시킵니다.
* bbox는 원본 이미지 좌표입니다. letterbox/resize 좌표를 역변환한 뒤 전달합니다.
* track_id는 해당 물체에 유지되는 uint32 ID입니다. 매 프레임 임의로 1을 넣어 동일 물체라고 속이지 않습니다.
* capture timestamp는 같은 호스트의 system-clock 기준 **노출 시각**입니다. GStreamer PTS/카메라 monotonic 시간을 그대로 epoch ns로 보내지 않습니다.
* 필요한 clock mapping을 실제 camera API로 검증합니다. 추론 종료의 time.time_ns()로 덮어써서 지연을 숨기지 않습니다.
* 연결/프레임 드롭은 send=False로 반환됩니다. sender가 receiver를 기다리며 장시간 막히지 않도록 했습니다.
* 같은 process stream에서 sequence/capture time은 증가해야 합니다. sender 재시작으로 stream_id가 바뀌면 receiver도 재시작합니다.

잘못된 schema·bbox·confidence·ID·시간·frame은 거절되고 기존 유효 observation은 갱신되지 않습니다.
탐지 없음은 정상 frame의 detections=[]로 전달하며 downstream에서 invalid가 됩니다.
socket은 파일 권한 기반 로컬 경계이고 인증/암호화 프로토콜이 아닙니다.

## 11. 탑재 승인 전 필요한 시험

1. Pi 네이티브 Docker image 빌드, Humble parameter API 및 ROS smoke.
2. 실제 Hailo 추론/추적/노출 시각/좌표와 socket 결과 대조, FPS·지연·드롭률 측정.
3. PX4 raw 상태와 adapter 출력, source 혼합·중단·재연결 시험.
4. 노드 crash/container stop, CPU/RAM/온도/저전압/저장공간 장시간 시험.
5. model/HEF/driver/runtime/image digest/config/firmware/msg SHA 기록.
6. Gazebo·지상시험과 별개로, 실비행 탑재의 전원·냉각·EMI·고정·운영 절차 검토.

자율비행 제어 검증은 이 코드의 완료 기준이 아닙니다. 실제 제어계가 필요하면 별도 guidance/command/failsafe 설계와 검증이 필요합니다.
