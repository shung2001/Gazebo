# YOLO11s 분할 모델의 Hailo-8 HEF 변환

`best_11s.pt`는 `target board` 한 클래스를 학습한 YOLO11s 분할 체크포인트다. 학습 입력 크기는 **1280×1280**이다. 기존 `hef/`의 YOLO11m 512px 작업과 산출물을 분리한다.

## 변환 방법

`hef/README.md`의 흐름을 따른다. WSL Ubuntu 22.04의 `/root/.venvs/we_meet_hailo8`에 Ultralytics 8.4.208 및 Hailo Dataflow Compiler 3.34.0이 설치된 환경을 사용한다.

```bash
cd /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s
bash ./compile_hailo8.sh
```

보정 데이터는 `../we_meet/dataset_11s_seg/train/images`에서 고른 64장의 고정 목록(`calibration_images.txt`)이다. Ultralytics가 `val`에서 보정 이미지를 읽으며, 전체 1,131장을 1280px float32로 한꺼번에 적재하면 약 20.7GiB가 필요해 이 목록을 사용한다. 128장과 최적화 수준 2의 조합도 WSL 메모리 부족으로 종료되어 64장과 최적화 수준 0으로 낮췄다. 원본 검증 이미지는 `valid/images`에 따로 있다. 데이터셋을 옮겼다면 YAML과 이미지 목록의 경로를 수정한다. 보정 이미지 64장은 권장 300장보다 적어 양자화 정확도 비교가 특히 중요하다.

스크립트는 `imgsz=1280`, `name=hailo8`, `hailo8` 아키텍처로 ONNX와 최적화 HAR를 만든 뒤 새 Python 프로세스에서 HEF를 컴파일한다. 메모리 사용을 줄이기 위해 DFC 최적화 수준 0, 양자화 후 파인튜닝 끔, 컴파일 탐색 수준 0을 적용한다. 성공 시 `best_11s_hailo_model/best_11s.hef`가 생성되며 같은 폴더의 `metadata.yaml`과 함께 보관한다. HAR에서 HEF만 다시 컴파일할 때는 `compile_saved_har.py`를 실행한다.

HEF의 실제 Hailo-8 장치 추론 속도와 분할 정확도는 별도 검증이 필요하다. 분할 출력은 박스·마스크 후처리를 거쳐 사용한다.

## 현재 실행 기록 (2026-11-25)

- 입력 체크포인트의 학습 크기 1280, 분할 작업, 단일 클래스를 확인했다.
- 1280×1280 ONNX를 중간 단계로 내보내고 최적화 HAR를 저장했다. Ultralytics가 Hailo 내보내기 완료 후 임시 ONNX를 삭제하므로 현재 남아 있는 중간 산출물은 HAR다.
- Hailo-8 컴파일은 단일 컨텍스트 배치에 실패해 3개 컨텍스트로 분할했다. 첫 컨텍스트 내부 배치를 약 33분, 2,200회 이상 탐색해도 HEF를 만들지 못해 이번 실행을 중단했다. 다시 시도할 때는 최적화 단계를 반복하지 않고 `/root/.venvs/we_meet_hailo8/bin/python compile_saved_har.py`를 실행한다.
