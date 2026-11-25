# 3인 개발 분담과 완료 기준

| 담당 | 소유 코드 | 구현·후속 과제 | 완료 기준 |
|---|---|---|---|
| A: Perception / Tracking | runtime/nodes.py의 MockPerception·Tracker, core.Tracker; detection/track msg | mock dropout·ID·시간 정책 이해; 이후 실제 detector bridge·camera calibration·latency 측정 | 유효/저신뢰/NaN/범위/중복/ID변경/중단 입력 검사; 원 observation timestamp 유지; ROS dropout 기록 |
| B: Mission / Guidance | core.Mission·proposal, nodes.Mission·Guidance; mission/proposal msg | 상태 전이·ABORT 복구; 영상 diagnostic와 물리 guidance 분리; 후속 카메라 기하·실행 가능 경로 연구 | IDLE→SEARCH→TRACK_SHADOW, status/track loss→ABORT, reset 시험; 유한·제한 출력; ROS smoke 통과 |
| C: Integration / Safety / PX4 | px4_status, nodes.SafetyGate·MockStatus, bringup, tools | 빌드 환경·contract gate·QoS·기록·검증 보고; 선택적 telemetry 통합 | colcon build/test, smoke, timeout, publisher 감사; 실제 firmware/hash/topic/type/시간 근거 기록; 제어 송신 없음 |

경로는 `src/alatus_runtime/alatus_runtime/` 기준입니다. 한 nodes.py에서 충돌하기 쉬우므로 각 담당은 자기 class만 수정하고
팀 리드가 통합합니다. 규모가 커지면 class별 파일로 나누되 entrypoint를 함께 갱신합니다.

## 진행 순서

1. 공동: AUDIT와 메시지를 읽고 문서 미확인 요구사항을 수집; 계약을 v0.1로 고정.
2. 각자 같은 기본 ZIP으로 환경 구축, 로직 테스트 및 ROS smoke 성공 증거 보관.
3. A는 detector adapter, B는 수학적 guidance specification, C는 read-only telemetry를 독립 개발.
4. 공동: 메시지 변경 PR에는 타입·단위·frame·time·validity·consumer 수정·테스트를 함께 포함.
5. C가 새 깨끗한 Ubuntu workspace에서 통합; A/B가 dropout와 ABORT 재현을 확인.
6. 실제 요구사항을 확인한 뒤 고정익 SITL 계획 수립. 제어 기능 추가는 이 starter의 설정 변경으로 진행하지 않음.

## 통합 승인에 필요한 증거

OS/ROS/Python 버전, git hash, colcon 결과, smoke 출력, topic info/QoS, rosbag, dropout 복구 결과를 남깁니다.
PX4는 firmware+px4_msgs+Agent+Gazebo/model commit을 추가합니다. 실제 카메라·Gazebo·기체 결과와 mock 결과를 구분합니다.
성능 목표와 기체 모델이 확정되지 않은 현재에는 회수 성공률·접근 정확도·실비행 안전성을 완료 기준으로 주장하지 않습니다.
