# 측정 방법과 실제 결과의 구분

실제 성능값은 없다. validation/metrics_template.csv의 value는 비어 있다. 단위시험의 합성 신호 결과는 항공기 성능표에 넣지 않는다.

| 지표 | 측정 방법 | 필요한 입력 |
|---|---|---|
| Precision/Recall/FP/FN/mAP | 독립 라벨 test set에서 confidence/IoU별 평가; Ultralytics val 사용 | 사용자 실제 모델+dataset yaml |
| FPS/Inference latency | warmup 분리, 입력 크기/runtime/device 고정, 프레임 처리 완료 monotonic interval 및 p50/p95/max | 실제 Video/Camera, 하드웨어 |
| Tracking RMSE | 동일 frame ID의 수작업 GT center와 KF center의 2D 유클리드 오차 RMSE | 라벨 center CSV+replay CSV |
| Prediction error/dropout recovery | GT가 있는 동일 영상의 통제된 frame dropout에서 age별 오차/재획득시간 | 분리된 영상 및 dropout 일정 |
| Covariance/Continuity | innovation/NIS, covariance와 실제 오차의 정합성, track ID 변경 횟수와 유효 프레임 비율 | TrackEstimate/GT |
| Bearing/Path error | 보정/시각 일치된 실제 LOS와 목표/실제 궤적 비교; image error와 구분 | Calibration, TF, 상태/경로 |
| Settling/Overshoot | 동일 초기조건의 step trial, 최종 error 허용band·유지시간을 사전 정의; zero step은 absolute tolerance | ROS bag+PX4 ULog |
| Saturation | saturated=true 시간 / 유효 제어 시간. 실제 PX4 actuator saturation은 ULog로 따로 측정 | VisualCommand+ULog |
| 비행 상태/응답 | Airspeed/ENU altitude/Attitude/Path/Turn과 명령을 동일 시각으로 겹쳐 분석 | PX4/Gazebo 실제 비행 |
| Abort/Failsafe | 표적/링크/카메라 손실의 주입시각부터 명령 중단·PX4 Mode 전환까지 각각 측정 | 장애 주입 로그+ULog |
| End-to-end delay | 실제 exposure timestamp→inference→track/guidance→MAVLink/PX4 수신/response 타임라인; clock mapping 기록 | 실제 capture 시각/trace/ULog |
| CPU/RAM/Jitter/Dropout | pidstat/docker stats/ROS Topic timestamp 및 sequence gaps, 장시간 temperature 조건 | 실제 장치 |

검출 평가 예시(실제 파일로 대체):

```bash
.venv/bin/yolo detect val model=/absolute/model.pt data=/absolute/dataset.yaml imgsz=640 split=test
ros2 topic hz /alatus/detection_frame
ros2 topic hz /alatus/visual_command
sudo apt install -y sysstat
pidstat -u -r 1
bash tools/record_metrics.sh log/test-run-name
```

Dataset은 촬영 Session/날짜/배경/거리별로 나누고 연속 프레임이 train/test에 중복되지 않게 한다. 실제 replay와 Gazebo synthetic 영상은 별도 데이터셋으로 보고한다. 모델 FPS 하나로 Closed-loop 안정성·포획 성능을 주장하지 않는다. V*total_latency로 접근거리 소모를 계산하되 V와 latency는 실측값을 넣는다.

실제 프레임 라벨 CSV(frame,u_px,v_px)가 있으면 다음 도구로 matched-frame RMSE를 계산한다. 입력이 없거나 유효 매칭이 없으면 수치를 만들지 않고 실패한다.

```bash
python3 tools/evaluate_tracking.py --track log/vision/replay.csv --truth /absolute/ground_truth.csv
```
