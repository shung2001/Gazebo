# 참고자료 적용 검토

첨부 PDF 세 편을 pdftotext -layout으로 추출하여 본문·방법·시험·결론을 검토했다. 수식 일부는 PDF 텍스트 추출 시 배열 기호가 사라지므로 해당 수식을 복사하지 않고 표준 CV Kalman 수식을 새로 구현하고 해석값 시험을 수행했다. 논문 수치/Gain/FPS를 ALATUS 값으로 전용하지 않았다.

| 자료 | 본문에서 확인한 내용 | 적용 | 적용하지 않는 내용 |
|---|---|---|---|
| Ma et al., Sensors 23, 8999 (2023) | Sec.3~5: Edge Computing, Jetson Xavier NX/TensorRT, YOLO 모델 비교, Gimbal Tracking, 지역을 달리한 인식 평가 | 온보드 전처리·추론·전송 경계 분리, 정확도와 FPS 동시 평가, 환경 변화 평가 | TensorRT 가속 성능을 Hailo-8 값으로 사용, Gimbal/PID를 고정익 경로제어로 치환 |
| 정효정 외, JASE 19(4), 17–26 (2025) | Sec.2.2~2.3, p.22~24: UAV dataset, YOLO 비교, 소형 물체/입력 해상도/threshold와 탐지 성능 관계 | 과녁 픽셀 크기·거리·threshold별 Precision/Recall 평가, 데이터 세션 분리 | UAV 검출 데이터 성능을 양궁 과녁/YOLO11m 결과로 주장, 대드론 충돌 유도 개념 전용 |
| Hassani & Nekoukar, JECEI 14(1), 227–240 (2026) | Sec.III~IV, p.233~234: YOLOv5, bbox center CV Kalman, 다중 후보 최근접, 단기 loss 예측, PD, 장기 loss 이후 retrieval | Detection→추정→외부제어 모듈 분리, 후보 Association, Prediction Timeout | 쿼드콥터 제자리 yaw/상하 이동, 오래된 error로 재검색 기동, 논문 PD Gain 그대로 복제 |
| MartinMohammed/object-tracking-yolo-v8-mil | README: YOLOv8n 주기 탐지 + 탐지 사이 MIL; 작성자의 MacBook 성능 | Detection/Tracking 구분, 추론 interval과 tracking update 분리의 필요성 | MIL 필수 설치, 해당 FPS를 ALATUS 요구/성능으로 사용 |

JECEI는 표적을 FOV 중앙에 유지하는 추적을 다루며 Net plane 통과를 입증하지 않는다. 본 구현은 최초 다중 검출 시 임의 confidence 승자를 고르지 않고 Ambiguous로 차단하며, 장기 Loss는 Mission ABORT와 PID reset으로 처리한다. 고정익은 hover나 측방속도 직접 명령을 사용할 수 없어 Course/Lookahead 위치 경로로 변경했다.

## 공식 문서 및 소스

- PX4 Offboard v1.17: https://docs.px4.io/v1.17/en/flight_modes/offboard
- PX4 Gazebo v1.17: https://docs.px4.io/v1.17/en/sim_gazebo_gz/
- PX4 수신 소스: https://github.com/PX4/PX4-Autopilot/blob/v1.17.0/src/modules/mavlink/mavlink_receiver.cpp
- PX4 FW mode manager: https://github.com/PX4/PX4-Autopilot/blob/v1.17.0/src/modules/fw_mode_manager/FixedWingModeManager.cpp
- MAVROS ROS2: https://github.com/mavlink/mavros/tree/ros2
- MAVROS Setpoint: https://github.com/mavlink/mavros/blob/ros2/mavros/src/plugins/setpoint_raw.cpp
- Gazebo Harmonic/Humble: https://gazebosim.org/docs/harmonic/ros_installation/
- ROS Humble: https://docs.ros.org/en/humble/ (해당 사이트 일부는 열람 시 Access Denied; 문서 전체 접근 성공으로 주장하지 않음)
- ROS 공식 문서 소스: https://github.com/ros2/ros2_documentation/tree/humble
- Ultralytics YOLO11: https://docs.ultralytics.com/models/yolo11/
- Ultralytics Predict: https://docs.ultralytics.com/modes/predict/
- Hailo Model Zoo: https://github.com/hailo-ai/hailo_model_zoo
- Raspberry Pi AI software: https://www.raspberrypi.com/documentation/computers/ai.html

원문 라이선스와 Ultralytics 모델/코드 사용조건은 실제 배포 시 확인한다. 논문 PDF와 타인의 가중치는 소스 ZIP에 재배포하지 않는다.
