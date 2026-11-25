# 04. Camera Geometry / Fixed-Wing PD-PID

## 1. 이번 단계의 목적

픽셀을 기체 경로오차와 구분하고 외부 유도 출력의 단위/부호를 검증한다.

## 2. 필요한 사전조건

02 Mock acceptance. 실제 Camera Calibration과 항공기 운용범위는 아직 TBD다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

```bash
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
bash tools/test_v04.sh
code src/alatus_vision/alatus_vision/geometry.py
code src/alatus_vision/alatus_vision/guidance.py
code src/alatus_vision/alatus_vision/pid.py
cp config/vision_sitl_shadow.yaml config/vision_sitl_local.yaml
code config/vision_sitl_local.yaml
```

실제 카메라 보정(ROS camera_calibration 도구를 쓰는 예):

```bash
sudo apt install -y ros-humble-camera-calibration
# camera image와 camera_info 토픽이 실제로 존재하는 터미널에서 실행
ros2 run camera_calibration cameracalibrator --help
ros2 run camera_calibration cameracalibrator --no-service-check --size 8x6 --square 0.024 --ros-args -r image:=/alatus/camera/image -r camera:=/alatus/camera
```

8x6은 내부 코너 수, 0.024 m는 예시 패턴 한 칸 크기다. 실제 출력한 패턴을 측정해 교체한다. 여러 기울기/거리/화면 모서리 표본을 수집하고 calibration 결과의 K/D/해상도/reprojection error를 보관한다. 자동초점 렌즈는 시험 초점 조건과 영상 해상도를 고정·기록한다.

config camera에는 fx/fy/cx/cy, distortion, resolution, optical_to_body_flu, position_body_flu_m를 넣고 calibrated=true로 바꾼다. 값이 없으면 null/false 그대로 두며 Guidance Invalid가 정상이다. Gazebo는 실제 CameraInfo와 Sensor 설정에서 확인한 값을 사용한다. 단순 FOV에서 계산한 nominal fx는 검증용 제안값일 뿐 실카메라 보정값이 아니다.

Lateral/Vertical Gain, Bank Limit, Min Airspeed, Local Altitude Floor/Ceiling, Lookahead, Horizon을 시험 모델에 맞게 검토하고 마지막에 controller_reviewed=true로 바꾼다. 실제 ALATUS 값을 만들지 않는다.

```bash
ros2 topic echo /alatus/visual_command --once
ros2 topic hz /alatus/visual_command
```

## 5. 전체 코드 또는 수정파일

geometry.py, pid.py, guidance.py 전체 파일과 tests/test_algorithms.py의 좌우/상하/해석값 시험을 확인한다. net_intersection은 별도 기하 입력 함수이며 자동 Capture 기능은 아니다.

## 6. 예상 출력

정면 중심에서 수평 error≈0, 오른쪽 표적은 ENU course correction 음수/Bank diagnostic 양수, 위 표적은 gamma 양수다. PX4 Roll/Pitch가 즉시 같은 값이 된다는 기대는 잘못이다.

## 7. 성공 판정

부호·단위·행렬·dt·출력 제한 시험을 통과하고 Shadow에서 실측 상태와 제안 경로를 비교한다. mock 숫자로 실비행 gain을 확정하지 않는다.

## 8. 대표적인 오류

CAMERA_CALIBRATION_TBD, Invalid extrinsic rotation, AIRCRAFT_STATE_INVALID, oscillation/saturation.

## 9. 오류 해결 방법

CameraInfo와 입력 해상도를 맞춘다. FLU/FRD 및 ENU/NED 이중 변환을 확인한다. 높은 error를 Gain 증가로만 해결하지 말고 시각 정합/지연/목표 도달가능성을 확인한다. PID_CONTROLLER_KO.md의 단계적 튜닝을 따른다.

## 10. 다음 단계와 연결

05 기본 비행과 06 Shadow를 먼저 통과한 후, 별도 Permit 검토가 끝나야 Closed-loop SITL 시험으로 간다.

## 저장 이미지로 보정하는 대안

ROS Camera 서비스가 없어도 실제 원본 이미지를 여러 각도로 저장한 뒤 OpenCV로 보정할 수 있다. 이미지 해상도/초점과 패턴 한 칸 실제 크기를 일치시킨다.

```bash
python3 tools/calibrate_camera.py --images '/absolute/path/calibration/*.png' --cols 8 --rows 6 --square-m 0.024 --output config/camera_measured.yaml
```

출력 RMS/view 수를 기록하고 별도 검증 이미지의 재투영 오차를 확인한다. Extrinsics는 null로 남으므로 장착 회전을 직접 측정한 뒤 Guidance config의 camera 블록으로 옮긴다. 카메라가 없는 현재 환경에서 이 도구의 실제 보정은 NOT TESTED다.
