# v0.3 검증 결과와 남은 통합

## 실제 실행한 검증

제작 PC: Windows / Python 3.12.14. ROS mock/stub를 만들어 ROS 실행을 흉내 내지 않았습니다.
`python tools/run_local_tests.py`의 순수 Python/소스/설정 검사 40개를 실행했습니다.
상세 결과: validation/local-tests.txt. ZIP CRC/파일 SHA256과 압축 해제 후 같은 테스트도 확인합니다.

검사 범위:

* 원래 freshness/observation/tracker/mission/guidance/gate 로직.
* 실행 schema와 문서 registry 대조 및 msg field 계약.
* 모든 parameter 기본값, 숫자 타입·범위·NaN/Inf, centre/amplitude·timer/age·gap 결합 검사.
* 변경한 tracker 확인 횟수/confidence/age, diagnostic gain/centre/limit 동작.
* 미래 timestamp가 accepted tracking watermark를 오염시키지 않음, reset 및 clock rewind/freeze latch.
* perception protocol의 timestamp/frame/sequence/stream/class/ID/bbox 검사와 deterministic 선택.
* PX4 profile review/version/SHA/definition hash/필드 type/enum/topic suffix 불일치 거절.
* 생성한 ROS YAML의 제한된 JSON-scalar 형식과 schema validation, consumer별 baseline 계약 일치.
* onboard launch에 Mock이 없음, non-privileged/read-only Compose 설정, Dockerfile의 시험 입력 포함.
* Python 구문, 4개 package XML, entrypoint, publisher가 ALATUS 진단 topic만 사용함.

마지막 항목들은 static 검사이며 Docker Compose 전체 schema 검증이나 ROS 실행 검증이 아닙니다.
profile fixture의 unit test는 선택 firmware가 실제로 연결된 증거가 아닙니다.

## 이 환경에서 수행하지 못한 검증

Docker executable, Ubuntu/ROS2 runtime, Raspberry Pi, camera, Hailo, PX4 hardware가 없습니다.
다음 사항은 NOT RUN입니다.

| 단계 | 상태 | 실행 도구/증거 |
|---|---|---|
| Ubuntu22.04 / Python3.10 build | NOT RUN | Docker build 및 colcon 결과 |
| 실제 ROS parameter descriptor/callback | NOT RUN | tools/ros_parameter_smoke.py |
| ROS mock topic/service 통합 | NOT RUN | tools/ros_smoke.py |
| arm64 Docker image/Compose 동작 | NOT RUN | Pi native build, compose config/up, 로그 |
| Linux socket→ROS 실통신 | NOT RUN | 원 observation/time/ID와 topic 대조 |
| Hailo-8 / Camera3 pipeline | NOT IMPLEMENTED HERE | 선택한 모델/HEF/driver/runtime와 hook 통합 필요 |
| PX4 Agent/VehicleStatus | NOT RUN | firmware/msg SHA, raw DDS와 adapter 비교 |
| Gazebo/지상/실비행 | NOT RUN | 별도 시험 기록 |
| 실제 aircraft control | NOT IMPLEMENTED | 별도 guidance/command/failsafe 설계 필요 |

## 현장에서 반복할 순서

1. Pi OS/arch/driver/runtime/temperature/power 기록.
2. Docker build → parameter API + Mock ROS acceptance.
3. Hailo 결과 protocol/time mapping 대조 → drop/latency/ID 시험.
4. 명시적으로 검토한 PX4 profile → read-only 상태 수신/중단/재연결 시험.
5. 장시간 부하/노드 crash/재부팅/clock fault 시험과 version/config 동결.

CPU/RAM/time/전력 값은 실제 측정 전 합격으로 판단하지 않습니다.
Docker health는 프로세스 관찰일 뿐 flight readiness가 아닙니다. control_allowed는 항상 false입니다.
