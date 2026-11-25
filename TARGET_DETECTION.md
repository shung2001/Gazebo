# 인하대 캠퍼스 VTOL 과녁 자동 탐지

기존 `run_vtol.sh`와 캠퍼스 월드는 유지합니다. 새 실행기는 캠퍼스 월드를 복제해 건물 벽에 붙은 2×2m 과녁을 사용합니다. VTOL 외형과 Gazebo 속도 제어 플러그인을 사용하며 PX4/MAVLink 비행 제어기를 호출하지 않습니다.

## 실행

PowerShell에서 프로젝트 폴더를 연 뒤:

```powershell
wsl -d Ubuntu-22.04 -- bash /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/run_target_detection.sh
```

화면 없이 기록만 만들려면 `--headless`를 추가합니다. `--duration 180`으로 최대 실행 시간을 지정할 수 있습니다.

기본 모델은 프로젝트 루트의 `YOLO11m_best.pt`입니다. 체크포인트를 직접 검사한 결과 분할 작업이며 클래스는 `{0: 'target board'}` 하나입니다. 다른 모델을 쓰려면 `--model /path/to/best.pt`를 지정할 수 있습니다. 선택한 모델에 `target board` 클래스가 없으면 실행을 중단합니다.

YOLO11s 1280px 체크포인트를 같은 월드·카메라 crop·기체 경로에서 비교하려면 프로젝트 루트의 PowerShell에서 다음을 실행합니다. 현재 WSL 가상환경의 protobuf와 Gazebo Python 바인딩이 충돌할 수 있어 실행 프로세스에만 호환 모드를 적용합니다.

화면에 탐지 박스를 표시하려면:

```powershell
wsl.exe -d Ubuntu-22.04 -- env PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python bash /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/run_target_detection.sh --model /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s/best_11s.pt --duration 180
```

화면 없이 CSV만 기록하려면:

```powershell
wsl.exe -d Ubuntu-22.04 -- env PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python bash /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/run_target_detection.sh --headless --model /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s/best_11s.pt --duration 180
```

이 명령은 `.pt`의 **Gazebo 영상 탐지 성능**을 측정합니다. Hailo 장치에서 HEF를 실행하는 시험은 아닙니다. 또한 현재 기체 접근 경로는 알려진 과녁 월드 좌표로 제어하고 YOLO 탐지 결과는 기록·표시에 사용합니다. 따라서 첫 탐지 거리와 탐지율은 비교할 수 있지만 영상 기반 폐루프 유도의 성공률은 측정하지 않습니다.

## 실험 조건

- 과녁: 기존 인하대 항공우주융합캠퍼스 건물 벽의 2×2m 패널. 중심 좌표는 `(-65.380811, -5.656304, 8)`m.
- 출발: 고도 60m, 동체 카메라에서 과녁 중심까지 3D 거리 100m. 카메라가 과녁을 바라보도록 동체 방향과 카메라 피치를 설정합니다.
- 접근: 과녁을 향해 직선으로 이동하며 고도를 함께 낮춥니다. 관성을 고려해 약 18m부터 수평 정지 명령을 내리고 약 15m에 도달하면 실험을 종료합니다. 수평 속도 명령의 상한은 4m/s이고, 실제 하강 속도에 맞춰 수평 진행을 조절합니다.
- 카메라: 동체 전방 3200×3200 RGB, 초당 1프레임. YOLO는 원본 화소의 중앙 1280×1280 영역을 사용합니다. UI는 전체 영상을 800×800으로 축소해 보여줍니다.

화면의 청록색은 카메라 자세로 계산한 과녁 위치이고, 초록색은 그 위치와 겹친 `target board` 예측 박스입니다. 박스에 클래스와 confidence를 표시합니다. 첫 탐지 거리는 해당 프레임 시각의 카메라에서 과녁 중심까지의 3D 거리입니다.

## 결과

`result/target_detection_YYYYMMDD_HHMMSS.csv`에 **시뮬레이션 시간 1초당 한 행**을 저장합니다. 각 행에는 위치, 고도, 과녁까지 거리, 해당 초의 카메라 프레임 수와 YOLO 박스 수, `target board` 탐지 여부와 최고 confidence, 첫 탐지 거리가 들어갑니다. 카메라 프레임이 없는 초에는 탐지 칸이 비어 있거나 0으로 표시됩니다.

`logs/target_detection_result.json`에는 마지막 상태와 첫 탐지 요약, `logs/target_detection_first.png`에는 첫 탐지 화면, `logs/target_detection_gazebo.log`에는 시뮬레이터 로그를 저장합니다.

현재 Ubuntu 의존성은 `/root/.venvs/we_meet_target` 가상환경의 CUDA PyTorch와 Ultralytics, Gazebo Harmonic 및 `python3-tk`입니다. 가상환경이 다르면 `TARGET_DETECTION_PYTHON`으로 Python 실행 파일을 지정할 수 있습니다.
