# INHA ALATUS ROS 2 Onboard Observer 0.3.0

Raspberry Pi 5 8GB / Raspberry Pi OS 호스트에서 Ubuntu 22.04 + ROS 2 Humble Docker를 실행하기 위한 소스입니다.
Hailo-8 26 TOPS / Camera Module 3은 사용자 확정 하드웨어이며, 정확한 OS release와 driver/runtime/HEF는 미확정입니다.

**실비행 검증이 완료된 비행 제어 소프트웨어가 아닙니다.** 기체 탑재용 관찰 시스템이며 aircraft command/arming/Offboard 송신은 없습니다.
control_allowed는 항상 false이고 Mission은 IDLE에서 시작합니다.

## 읽는 순서

1. [Raspberry Pi Docker Walkthrough](docs/RPI_DOCKER_WALKTHROUGH_KO.md)
2. [실제 구현 파라미터](docs/IMPLEMENTED_PARAMETERS_V03_KO.md)
3. [Hailo/카메라/모델 선택 및 연결](docs/HAILO8_MODEL_AND_CAMERA_KO.md)
4. [현재 검증 결과](docs/VALIDATION.md)

## 실제 구현

* 4개 ROS 패키지, 0.3.0: interfaces / runtime / bringup / optional px4_status.
* 기존 제안 파라미터를 실제 선언·read_only·범위/결합 검사·실행 로직에 연결.
* mock 개발 launch와 실제 데이터 대기용 onboard observer launch 분리. 탑재 기본값에 mock 없음.
* 원 관측 stamp 유지, tracker 미래 timestamp 문제·stale count 수정, source/중복 publisher 검사.
* monotonic receipt/timer와 clock fault latch. PX4 failsafe/독립 비행 watchdog을 대체하지 않음.
* Unix datagram JSON 추론 결과 → typed ROS Detection. 실제 Hailo inference/HEF는 포함하지 않음.
* PX4 firmware 변경에 대비한 명시적 compatibility profile, installed msg SHA256/type/version/enum 검사.
* arm64 Dockerfile, Compose, non-root observer, writable data/socket만 mount, health probe, ROS acceptance 도구.

## 실행과 검증

ROS 없이: `python3 tools/run_local_tests.py`.
Ubuntu/Humble 환경에서: `bash tools/validate_humble.sh` (실제 ROS build/API/smoke acceptance용).
Raspberry Pi Docker 절차는 위 Walkthrough를 따르십시오.
제작 PC에서는 순수 Python/소스·설정 검사만 실행했습니다. ROS/Docker/Pi/Hailo/PX4 실행은 아직 검증하지 못했습니다.

기존 v0.1/v0.2 문서는 설계 이력이며 현재 파라미터·PX4 profile·배포 절차는 v0.3 문서가 우선합니다.
원본 프로젝트 PDF·기체 공력/회수 요구조건은 미확보이므로 모든 ALATUS 요구조건 충족을 주장하지 않습니다.
