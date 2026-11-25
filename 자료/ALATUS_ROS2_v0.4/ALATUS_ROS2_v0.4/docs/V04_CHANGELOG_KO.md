# v0.3 → v0.4 변경 및 보존

## 실제 비교 결과

| 파일/디렉터리 | v0.4 처리 |
|---|---|
| core.py, clock_guard.py, perception_protocol.py | 바이트 그대로 유지; 새 Pipeline이 Mission/ClockGuard 재사용 |
| nodes.py, perception_socket.py | 기존 실행 유지, 신규 경로에서는 대체 노드 사용 |
| 기존 6개 .msg | 바이트 그대로 유지; 인터페이스 ABI를 무조건 바꾸지 않음 |
| alatus_px4_status | legacy_alatus_px4_status로 이동하고 COLCON_IGNORE |
| src/alatus_bringup/launch/shadow.launch.py | 기존 Mock 진단 회귀용 유지 |
| onboard_observer.launch.py | v0.4 onboard_shadow 별칭; 구버전은 legacy_onboard_observer.launch.py |
| deploy/Dockerfile, compose.yaml, onboard.yaml | v0.4 기본 파일로 교체; 원본은 regression/v03/deploy에 보존 |
| tools/validate_humble.sh | v0.4 acceptance 스크립트로 위임 |
| tests/ | v0.4 pytest; 원본 40개는 regression/v03/tests |
| docs/ | 신규 문서; 기존 것은 docs/legacy_v03 |

추가 메시지: PixelDetection, DetectionFrame, TrackEstimate, AircraftState, VisualCommand.
추가 알고리즘: Variable-dt Kalman/Joseph update/Mahalanobis gating, PD/PID, 광학 좌표변환, 제한된 Course Lookahead, MAVROS 상태/위치 송신기.
추가 노드: vision_perception, vision_pipeline, mavros_state_adapter, sitl_command_sender.

삭제한 원본 기능은 없다. DDS는 기본 소스 검색 대상에서 격리했다. 기본 onboard observer는 MAVROS이며 DDS와 동시에 AircraftStatus를 발행하지 않는다. 구버전 Legacy Launch는 수동 회귀용이고 DDS를 빌드/활성화하려면 별도 작업공간을 사용한다.

## 원본 보존 확인

regression/v03는 첨부 ZIP의 v0.3/ALATUS_ROS2_STARTER 전체 복사다. regression/COLCON_IGNORE로 중복 패키지 검색을 막는다. SOURCE_PROVENANCE.json에는 ZIP SHA256 및 보존 파일 해시를 기록했다. 신규 테스트는 핵심 순수 로직과 메시지 바이트 불변성을 검사한다. 구버전 회귀시험의 PASS는 그 구버전 계약의 보존을 뜻하며 MAVROS/신규 ROS 런타임 PASS를 뜻하지 않는다.

## 재현

```bash
bash tools/test_v04.sh
bash tools/validate_humble_v04.sh
```

첫 명령은 현재 환경에서 실행했다. 두 번째는 Humble 설치가 있는 PC/CI에서 수행해야 한다. 신규 실행 로그와 NOT TESTED 경계는 VALIDATION.md를 따른다.
