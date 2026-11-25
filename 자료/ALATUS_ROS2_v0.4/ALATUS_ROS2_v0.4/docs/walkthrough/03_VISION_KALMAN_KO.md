# 03. YOLO11m / Video / Kalman

## 1. 이번 단계의 목적

실제 사용자 모델을 검사하고 녹화 영상으로 추적과 Loss를 평가한다.

## 2. 필요한 사전조건

사용자 학습 .pt와 실제 과녁 영상. 둘 다 현재 첨부되지 않아 실제 추론 결과는 BLOCKED다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

의존성을 시스템 Python에 sudo pip로 덮어쓰지 않는다. 별도 Vision venv를 사용한다:

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
source /opt/ros/humble/setup.bash
source install/setup.bash
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python3 -m pip install -r requirements-vision.txt
.venv/bin/python3 -c 'import cv2,numpy,ultralytics; from cv_bridge import CvBridge; print(numpy.__version__)'
.venv/bin/python3 tools/inspect_model.py /absolute/path/to/your_model.pt --imgsz 640
cp config/video_shadow.yaml config/video_local.yaml
code config/video_local.yaml
```

video_local.yaml에서 model_path, video_path는 실제 절대경로로 수정한다. inspect 출력의 실제 class_id를 반영한다. imgsz도 모델 평가에 맞게 정한다. 카메라 calibration과 제어 변수는 04를 따라 채운다. Detection/Tracking만 보려면 controller_reviewed=false를 유지해도 된다.

```bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
ros2 launch alatus_bringup video_shadow.launch.py config_path:="$PWD/config/video_local.yaml" perception_prefix:="$PWD/.venv/bin/python3"
```

다른 터미널 source 후:

```bash
ros2 topic echo /alatus/detection_frame --once
ros2 topic echo /alatus/track_estimate --once
```

별도 Offline CSV/Overlay:

```bash
mkdir -p log/vision
export PYTHONPATH="$PWD/src/alatus_vision:$PWD/src/alatus_runtime:$PWD/src/alatus_mavros"
.venv/bin/python3 tools/replay_offline.py --model /absolute/path/to/your_model.pt --video /absolute/path/to/video.mp4 --class-id 0 --output log/vision/replay.csv --show
.venv/bin/python3 -m pip freeze > log/vision/python-resolved.txt
```

class-id 0은 명령 예시이며 실제 class로 교체한다. Mock Loss 시험은 02의 mock_shadow에서:

```bash
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
ros2 param set /vision_perception dropout true
ros2 topic echo /alatus/mission_state --once
ros2 param set /vision_perception dropout false
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: false}'
ros2 service call /alatus/shadow_mission std_srvs/srv/SetBool '{data: true}'
```

## 5. 전체 코드 또는 수정파일

src/alatus_vision/alatus_vision/yolo.py, tracking.py, perception_node.py, tools/inspect_model.py, tools/replay_offline.py가 전체 구현이다. VISION_KALMAN_KO.md에 수학과 Hailo 경계를 설명했다.

## 6. 예상 출력

모델 메타데이터와 원본 이미지 크기/픽셀 bbox가 출력된다. 검출 없는 프레임은 빈 배열이다. EOF 뒤 입력은 멈추고 Track이 만료한다. 오래된 영상 프레임을 무한 반복해 정상 관측처럼 갱신하지 않는다.

## 7. 성공 판정

Box와 영상 Overlay가 일치한다. 클래스/좌표/시각/다중 후보가 맞고 Loss 시 Track/Guidance가 무효가 된다. 실제 정확도는 분리된 라벨 dataset으로 별도 측정한다.

## 8. 대표적인 오류

MODEL_FILE_NOT_PROVIDED, class mismatch, NumPy ABI error, 영상 추론이 느려 모든 입력 stale.

## 9. 오류 해결 방법

실제 경로/names를 확인한다. NumPy<2와 호환 OpenCV/torch 환경을 검토한다. perception_prefix로 venv Python이 실제 실행되는지 ps에서 확인한다. 지연이 요구보다 크면 모델/입력 해상도/가속 경로를 재평가하며 timeout을 무조건 늘려 성공 처리하지 않는다.

## 10. 다음 단계와 연결

04에서 Calibration과 Guidance를 연결한다. HEF는 별도로 07의 하드웨어 검증을 수행한다.
