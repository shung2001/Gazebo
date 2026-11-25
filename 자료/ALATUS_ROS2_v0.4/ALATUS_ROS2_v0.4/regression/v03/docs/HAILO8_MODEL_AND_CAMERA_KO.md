# Hailo-8 / Camera Module 3 연결과 모델 선택

## 확정한 하드웨어와 남은 결정

사용자 확정: Raspberry Pi 5, RAM8GB, Raspberry Pi OS(사용자 표현 Raspbian), Hailo-8 26TOPS, Camera Module 3.
OS의 정확한 release와 64-bit 여부, 카메라 standard/wide/NoIR 종류, driver/runtime/firmware, 모델과 HEF는 아직 미정입니다.
이 문서는 특정 모델의 비행 인식 성능이나 FPS를 보장하지 않습니다.

## 소프트웨어 경계

이번 기본 배치는 카메라/Hailo pipeline을 호스트에서, ROS 2 Humble을 Ubuntu 22.04 container에서 실행합니다.
호스트 Python 버전과 ROS Python3.10의 ABI를 분리하고 inference 결과만 Unix datagram으로 전달합니다.
ROS container에는 카메라·PCIe device가 전달되지 않습니다. Hailo driver도 설치하지 않습니다.
container 내부 추론이 반드시 필요하면 정확한 aarch64 HailoRT/Python wheel/driver 호환 조합을 확보한 후 별도 image를 만들어야 합니다.
이번 image에 `pip install hailo` 같은 검증되지 않은 설치 명령은 없습니다.

[Raspberry Pi 공식 AI 문서](https://www.raspberrypi.com/documentation/computers/ai.html)는 카메라/HAT/OS 조건과 설치 경로를 제공합니다.
[HailoRT 공식 저장소](https://github.com/hailo-ai/hailort)는 Hailo-8 계열에 hailo8 branch를 구분합니다.
[Hailo Apps 공식 설정](https://github.com/hailo-ai/hailo-apps/blob/main/hailo_apps/config/config.yaml)은 Hailo-8과 Hailo-10의 runtime/TAPPAS 조합을 별도로 관리합니다.
실제 설치 때 선택한 release의 문서를 따라 설치하고 버전을 동결합니다. master/latest를 임의로 섞지 않습니다.

## 모델을 고르기 전에 필요한 질문

1. 표적은 회수망 전체, 과녁 무늬, 특정 마커, 다른 객체 중 무엇입니까?
2. 표적의 실제 크기·외형·종류와 거리/각도/조명/배경 범위는 무엇입니까?
3. 회수 접근에서 필요한 것은 bbox/중심점입니까, 표적 자세/3D 위치입니까?
4. 카메라 해상도/FPS/FOV와 장착 방향, 예상 표적 픽셀 크기, 모션 블러·노출 범위는 무엇입니까?
5. 반드시 지켜야 할 false positive/false negative, end-to-end 지연, 연속 상실 허용시간이 있습니까?
6. 팀에 실제 촬영 데이터와 annotation, calibration/실측 ground truth가 있습니까?

이 정보 없이 특정 YOLO 모델, confidence0.7, 30FPS, 인식 거리 등을 ALATUS 확정값으로 정하지 않습니다.

## 후보 접근의 비교

| 접근 | 고려할 조건 | 별도 검증 |
|---|---|---|
| 규격 마커/기하 기반 | 표적에 알려진 패턴을 배치할 수 있고 해상도·각도가 충분한 경우 | pose ambiguity, 거리·기울기·블러, 오검출, 실제 인식 한계 |
| 경량 learned detector + tracker | 표적 외형/배경이 다양하고 충분한 학습 데이터가 있는 경우 | Hailo-8 지원 graph/HEF, 양자화 손실, class map, 작은 표적 recall |
| detector + keypoint/geometry 후처리 | bbox만으로 접근 방향/망 자세를 결정할 수 없는 경우 | keypoint/pose ground truth, camera geometry, 지연·계산량 |

모델 이름보다 이 입력·출력 계약과 실제 표적 평가를 먼저 고정합니다.
Hailo Model Zoo의 compiled HEF는 장치 target과 runtime을 확인해야 합니다. Hailo-8과 Hailo-8L/10H용 모델을 동일하게 취급하지 않습니다.
[Hailo 공식 Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)

## 평가 절차

1. 실카메라의 촬영·노출 timestamp와 원 해상도 frame을 저장합니다.
2. 학습/검증/시험 데이터를 촬영 세션·배경·날짜 기준으로 분리하여 유사 프레임 유출을 줄입니다.
3. 표적 pixel size·거리·각도·조명·블러별로 detection recall/false positive와 centre error를 측정합니다.
4. 양자화/HEF 전후 출력 차이와 실제 Hailo-8 장치의 inference latency를 비교합니다.
5. end-to-end exposure→ROS track latency의 median/p95/p99, frame drops, tracker ID switch를 측정합니다.
6. 열/전원/CPU/RAM 상태에서 반복합니다. 26TOPS 숫자를 실제 pipeline FPS로 환산하지 않습니다.
7. Mission dropout/ABORT와 통합하고 기록을 검토한 뒤 모델·runtime·config SHA를 동결합니다.

수치 합격 기준은 비행속도·허용 접근오차·기동/회수 조건에서 역산해야 합니다. 현재는 요구자료가 없어 미정입니다.

## 전달 hook 사용 조건

integration/hailo_result_client.py의 ResultClient는 선택된 pipeline의 callback에 연결하는 transport client입니다.
실제 Hailo API 호출, camera capture, HEF loading, NMS decoding, multi-object tracker는 이 client에 구현되어 있지 않습니다.
사용 중인 vendor example의 해당 release/commit과 모델 출력이 정해지면 그 부분을 구현해야 합니다.

반드시 확인할 값:

* capture_stamp_ns: 같은 호스트 system-clock의 노출 시각. camera monotonic/PTS이면 검증된 mapping 필요.
* image_width/height: 원 image 크기. network 입력 tensor 크기와 혼동하지 않음.
* bbox_xywh_px: 원 image 좌표; resize/letterbox/crop inverse mapping 수행.
* track_id: stable uint32. detector 단독에는 ID가 없을 수 있어 tracker 구현 필요.
* class_id: 실제 class label; receiver target_class_id와 일치.

stream/session이 바뀌면 receiver도 재시작합니다. graph와 frame freshness가 다시 확인된 뒤 운영자가 shadow 분석을 시작합니다.
인식 연결이 성공해도 correction_norm은 무차원 진단값이며 실제 비행 제어 입력이 아닙니다.
