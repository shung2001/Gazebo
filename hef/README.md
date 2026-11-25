# YOLO11m 표적 모델의 Hailo-8 HEF 변환

1280×1280 입력의 YOLO11s 분할 체크포인트 `hef_11s/best_11s.pt` 변환 절차와 실행 기록은 [별도 가이드](../hef_11s/README.md)에 있다. 기존 YOLO11m 512px 산출물과 분리해 관리한다.

## 현재 상태

- `YOLO11m_best.pt`: 원본과 동일한 체크포인트. YOLO11 인스턴스 분할, `target board` 1개 클래스, 입력 512×512.
- `YOLO11m_best.onnx`: Ubuntu 22.04의 Ultralytics 8.4.208에서 opset 11, 그래프 단순화, NMS 제외 옵션으로 내보낸 중간 파일. ONNX 그래프 검사를 통과했다. 배포용 HEF는 아니다.
- `calibration_data.yaml`: 원래 학습 데이터셋을 WSL 경로로 참조한다. Ultralytics가 `val` 경로에서 보정 이미지를 읽으므로, 보정용 `val`을 학습 이미지 1,866장에 연결했다. 별도 검증 이미지 163장은 원본 데이터셋에 있다. 데이터셋을 옮겼다면 `path`를 수정해야 한다.
- `verify_inputs.py`: ONNX 구조와 데이터셋 경로를 다시 확인한다.
- `YOLO11m_best_optimized.har`: DFC가 생성한 양자화된 중간 모델.
- `YOLO11m_best_hailo_model/YOLO11m_best.hef`: **Hailo-8용 컴파일 완료 파일**, 26,877,685바이트. SHA-256: `43165F1B308A47C3259C691038EA96A2A92336E137C1B32BC6189A69CC98B62D`.
- `YOLO11m_best_hailo_model/metadata.yaml`: 분할 작업, 512×512 입력, 단일 클래스, `hailo8` 아키텍처 정보. HEF와 함께 보관한다.
- DFC 3.34.0을 컴파일 전용 Ubuntu 환경에 설치했다. Ultralytics의 기본 4회 양자화 학습은 WSL의 15GB 메모리 한도에서 OOM으로 종료됐다. `export_hailo8.py`는 이 학습을 비활성화하고 최적화 결과를 HAR로 저장한다. `compile_saved_har.py`는 새 Python 프로세스에서 HAR를 HEF로 컴파일하여 메모리 누적을 줄이고, 컴파일 탐색 수준을 0으로 설정한다. 이 설정은 추론 속도에 영향을 줄 수 있다. 생성된 HEF의 정확도와 속도는 별도 검증이 필요하다.
- `.pt` 복사본, ONNX, HAR, DFC 설치 파일과 로그는 용량 때문에 Git에 올리지 않는다. 이 PC의 `hef` 폴더에는 남아 있으며, 새 복제본에서 스크립트를 실행하면 루트의 `YOLO11m_best.pt`를 `hef`로 복사한다.

## 다시 컴파일하는 방법

현재 PC의 `hef` 폴더에 Hailo-8/8L용 **DFC 3.34.0, Linux x86_64** 설치 파일이 있고 컴파일 전용 Ubuntu 환경에도 설치되어 있다. 설치 파일은 Git에 포함되지 않는다. 다른 PC에서는 [Hailo Developer Zone 소프트웨어 다운로드](https://hailo.ai/developer-zone/software-downloads/)에서 같은 계열의 DFC를 설치해야 한다.

Ubuntu x86_64에서 아래 명령을 실행한다. 현재 WSL Ubuntu 22.04에 컴파일 전용 `/root/.venvs/we_meet_hailo8` 환경을 만들고 DFC 3.34.0, CPU용 PyTorch, Ultralytics 8.4.208을 설치했다. 문제가 생기면 네이티브 Ubuntu x86_64에서 같은 과정을 실행한다.

```bash
cd /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef
/root/.venvs/we_meet_hailo8/bin/python verify_inputs.py
bash ./compile_hailo8.sh
```

`compile_hailo8.sh`는 체크포인트에서 Hailo-8 HAR를 만들고 별도 프로세스에서 HEF로 컴파일한다. 설정은 `name=hailo8`, `imgsz=512`, `data=calibration_data.yaml`이다. 실제 DFC 모델 스크립트는 `model_script.alls`에 남긴다. 성공하면 생성된 Hailo 모델 폴더의 `.hef`와 `metadata.yaml`을 함께 보관한다. YOLO11 분할 HEF는 원시 출력 텐서를 내므로, Ultralytics 외의 HailoRT 코드에서 사용하려면 박스·마스크 후처리가 필요하다.

이미 저장된 HAR에서 HEF만 다시 생성하려면 `/root/.venvs/we_meet_hailo8/bin/python compile_saved_har.py`를 실행한다. 실제 Hailo-8 장치에서의 마스크 정확도와 추론 속도는 아직 측정하지 않았다. 양자화 학습을 생략하고 컴파일 탐색 수준을 낮춘 결과물이므로, 배포 전에 원본 체크포인트와 비교해야 한다.
