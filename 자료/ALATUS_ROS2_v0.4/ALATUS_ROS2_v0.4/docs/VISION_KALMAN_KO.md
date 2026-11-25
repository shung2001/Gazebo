# 비전 및 Kalman 설계

## 실제 모델과 입력

학습 YOLO11m 파일은 제공되지 않았다. 클래스명, 실제 입력 Tensor, HEF Output, DFC/HailoRT 호환성 및 정확도는 BLOCKED다. .pt Adapter는 경로 존재를 검사하고 Ultralytics 공식 API에 전처리/Letterbox/NMS/원본 좌표 복원을 맡긴다. bgr8 numpy 프레임을 넘기고 Results.boxes.xyxy를 사용한다. 임의의 Raw Tensor Layout을 만들지 않는다. 모델은 신뢰할 수 있는 사용자 파일만 로딩한다.

```bash
python3 tools/inspect_model.py /absolute/path/to/model.pt --imgsz 640
```

640은 요청 입력 크기의 예시다. 학습·배포 해상도를 실제 모델과 비교해서 결정한다. 출력 names/task/orig_shape/boxes/speed와 SHA를 기록한다. Zero Image smoke는 탐지 정확도 시험이 아니다. Raw graph normalization, ONNX nodes, tensor outputs와 Hailo 후처리는 모델 확보 후 추가 검토해야 한다.

DetectionFrame은 원본 픽셀 xyxy, 정수 Class ID, confidence, 이미지 크기, source stream UUID, sequence, 촬영 시각을 담는다. 검출 없음은 빈 배열이다. Class/Confidence/Finite/양의 박스/경계 검사를 통과해야 한다. 최초 복수 후보는 임의 선택하지 않고 AMBIGUOUS로 둔다. 추적 후에는 Mahalanobis 거리로 Association하고 거의 동일 후보가 있으면 명령을 막는다. 임의의 ID가 바뀐 객체를 계속 같은 과녁으로 취급하지 않는다. 외형/색/과녁 ID 분류는 아직 추가되지 않았다.

## 수학

상태 [u,v,u_dot,v_dot], 측정 [u,v], 단위 px, px/s다. F의 (0,2),(1,3)은 실제 dt다. G=[[dt²/2,0],[0,dt²/2],[dt,0],[0,dt]], Q=q GGᵀ이며 q는 구간 내 일정한 랜덤 가속도의 분산이다. 연속시간 백색가속도 모델의 Q와 혼동하지 않는다. R=r I₂, 초기 P=diag(r,r,400,400)은 시험용 설정이다.

Innovation y=z-Hx, S=HPHᵀ+R, d²=yᵀS⁻¹y로 Gating한다. K는 역행렬 직접 계산 대신 solve로 구한다. P 갱신은 Joseph form이다. gate=9.21은 초기 2차원 게이트 제안값일 뿐 실제 탐지 분포의 검증값이 아니다. q,r,P/최대분산은 실측 중심 오차로 추정해야 한다.

측정시각 내부 상태와 현재시각 projection을 분리하여 Timer가 오래된 관측을 새 관측으로 만들지 않는다. sequence 역행/중복 timestamp/future/stale 입력은 거부한다. source나 해상도 변경은 재확인한다. 3회 확인, 예측 유효 0.15초, 장기 Timeout 0.5초, 명령 관측 age 0.1초는 소프트웨어 시험용 초기값이다. 실제 접근속도와 지연 예산으로 재설정한다. 가림 중 예측은 존재할 수 있지만 공분산/age 초과 시 Guidance를 끈다.

## 카메라 운동과 지연

world ENU LOS 계산은 기체 자세를 반영한다. 하지만 이 버전은 측정시각 자세 보간, 카메라 회전에 따른 Kalman 상태 전파, rolling shutter, 고정 지연 보상을 구현하지 않았다. 광학 속도는 실제 Target Velocity가 아니다. 큰 Roll/Pitch, 빠른 접근, 원근 비선형, 가변 추론 지연에서 CV 가정이 깨지면 attitude timestamp buffer, derotation, EKF/UKF 또는 inverse-depth bearing filter를 검토한다. EKF로 바꾸는 것만으로 단안 range가 관측되는 것은 아니다.

## Hailo

Host의 실제 Camera/Hailo 파이프라인은 기존 integration/hailo_result_client.py ResultClient에 exposure timestamp와 원본 이미지 xywh를 전달한다. v0.4 Socket 경계가 이를 픽셀 DetectionFrame으로 변환한다. 기존 schema는 class_id 문자열, stable unique track_id를 요구한다. 실제 클래스명은 config의 hailo_class_name으로 매핑한다. 여러 검출에 같은 track_id를 넣으면 거부된다.

Model Zoo 공식 master는 Hailo-10/15 경로이며 Hailo-8/8L은 v2.x + DFC v3.x 경로를 확인해야 한다. 이 사실만으로 사용자 YOLO11m HEF 컴파일 성공을 의미하지 않는다. 모델 그래프, 최적화 calibration dataset, 양자화 오차, HAILO8 target, NMS 출력, HailoRT/Driver를 함께 검증한다. 실제 SDK가 없어 가짜 Hailo 추론 코드를 넣지 않았다.
