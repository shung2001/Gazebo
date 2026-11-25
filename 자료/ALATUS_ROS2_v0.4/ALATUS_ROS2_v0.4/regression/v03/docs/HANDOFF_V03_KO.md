# 새 GPT용 v0.3 추가 인수인계

첨부한 ALATUS_ROS2_ONBOARD_v0.3.zip의 실제 코드와 README를 먼저 읽어 주세요.
이 파일은 이전 인수인계의 다음 내용을 갱신합니다.

* 확정 하드웨어: Raspberry Pi 5 8GB, Raspberry Pi OS(사용자 표현 Raspbian), Hailo-8 26TOPS, Camera Module 3.
* OS 정확한 release/64-bit 여부·HailoRT/driver·카메라 파이프라인은 아직 현장 확인 필요.
* 모델/HEF는 미정. 실제 표적·데이터·거리/각도/지연 요구를 논의한 뒤 선택해야 함.
* ROS 패키지 버전 0.3.0: v0.2 제안 파라미터 구현 완료. application 설정은 startup/read_only, dropout만 runtime.
* runtime schema: alatus_runtime/parameter_specs.py. 검증: parameters.py. ROS 연결: ros_parameters.py 및 nodes.py.
* onset 미래 timestamp poisoning·stale hit count를 수정하고 monotonic receipt/clock guard와 source/중복 publisher 검사를 추가.
* Docker onboard launch에는 mock 없음. mission IDLE, PX4 adapter disabled가 기본. aircraft command는 없고 gate는 항상 false.
* Hailo 추론은 호스트의 검증된 pipeline에서 실행하는 설계. ROS Ubuntu 컨테이너는 Unix datagram 추론 결과만 받음.
* ResultClient는 transport hook일 뿐 HEF loading/camera/NMS/tracker가 아님. vendor pipeline callback 연결은 모델 선정 후 구현 필요.
* PX4 버전이 바뀔 수 있어 v1.16 고정 gate를 reviewed compatibility JSON profile로 교체.
* 2026-11-02 조회 official latest stable은 v1.17.0. profile template은 unreviewed이며 firmware/msg SHA와 installed msg SHA256/type/version/enum을 확인해야 활성화 가능.
* 40개 순수 Python/소스/설정 테스트 통과. Docker/ROS API/Pi/Hailo/PX4/실비행은 제작 환경에서 실행하지 못함.
* 실제 ROS acceptance: tools/ros_parameter_smoke.py, tools/ros_smoke.py, tools/validate_humble.sh. 제공됐다는 사실을 실행 성공으로 표현하지 말 것.
* 현재 실행 문서는 RPI_DOCKER_WALKTHROUGH_KO.md와 IMPLEMENTED_PARAMETERS_V03_KO.md가 우선. 이전 v0.1/v0.2 문서는 이력.
* PX4 수신 timestamp를 무조건 boot time으로 해석하지 말 것. DDS offset/time-sync 설정을 실제 확인해야 함.
* 원본 프로젝트 PDF·기체 공력·회수 조건은 여전히 미확보. 실제 비행 제어계 완성이나 전 요구조건 충족을 주장하지 말 것.

모델 논의는 docs/HAILO8_MODEL_AND_CAMERA_KO.md의 질문부터 시작해 주세요.
