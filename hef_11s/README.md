# YOLO11s 분할 모델: 1280px Hailo-8 HEF

`best_11s.pt`는 `target board` 한 클래스를 학습한 YOLO11s 인스턴스 분할 모델이다. 학습 크기와 이 폴더의 HEF 입력 크기는 모두 **1280×1280**이다. HEF는 **Hailo-8**용으로 컴파일했다. Hailo-8L용 HEF와 혼용할 수 없다. 기존 `../hef/`의 YOLO11m 512px 작업과는 별개다.

## 현재 결과

| 항목 | 확인된 값 |
| --- | --- |
| HEF | `best_11s_hailo_model/best_11s.hef` |
| HEF 크기 | 26,443,818바이트 |
| HEF SHA-256 | `7895e1d949994d8ce245d44e082ca10e51c67da867dd2c37340d3c304d13f018` |
| 입력·작업·클래스 | 1280×1280, `segment`, `target board` 1개 |
| 최적화 HAR | `best_11s_optimized.har` (205,393,920바이트) |
| 도구 | WSL Ubuntu 22.04, Ultralytics 8.4.208, Hailo Dataflow Compiler 3.34.0 |

HEF 파일의 존재·크기·해시는 확인했다. **실제 Hailo-8 장치에서의 추론, FPS, 분할 정확도는 아직 검증하지 않았다.** `metadata.yaml`을 HEF와 같은 폴더에 보관한다.

## 파일과 생성 방식

| 파일 | 생성·관리 방식과 역할 |
| --- | --- |
| `best_11s.pt` | 외부 학습 결과인 원본 PyTorch 체크포인트. 아래 Python 스크립트가 생성하는 파일은 아니다. |
| `calibration_data.yaml` | 사람이 작성한 보정 데이터 설정. 학습 데이터셋의 위치와 `val`에 연결한 보정 이미지 목록을 지정한다. |
| `calibration_images.txt` | 학습 이미지 1,131장 가운데 파일명 순서로 고르게 선택한 64장의 WSL 절대 경로 목록. 양자화 보정에 사용한다. |
| `export_hailo8.py` | 이 작업용으로 작성한 1단계 Python 스크립트. `.pt`를 1280px ONNX로 내보내고, Hailo 모델을 파싱·INT8 보정·최적화한 후 `best_11s_optimized.har`를 저장한다. 아래 상세 설명 참고. |
| `model_script.alls` | `export_hailo8.py`가 Ultralytics에서 받은 DFC 설정을 수정해 자동 기록한 파일. 정규화, 최적화 수준 0, 양자화 후 파인튜닝 비활성화, 출력 활성화 설정이 들어 있다. |
| `best_11s_optimized.har` | `export_hailo8.py`가 저장한 **최적화 완료 중간 모델**. HEF 컴파일만 재시도할 때 입력으로 사용한다. |
| `compile_saved_har.py` | 2단계 Python 스크립트의 **컴파일 탐색 수준 0** 버전. HAR를 읽어 HEF를 생성한다. 1280 모델에서는 배치 탐색 시간 초과가 발생했으므로 현재 결과의 재현에는 아래 `max` 버전을 사용한다. |
| `compile_saved_har_max.py` | `compile_saved_har.py`를 복사해 `performance_param(compiler_optimization_level=max)`로 바꾼 버전. 저장된 1280 HAR만 다시 읽어 `best_11s_hailo_model/best_11s.hef`에 쓴다. 보정은 반복하지 않는다. |
| `compile_hailo8.sh` | 환경·데이터셋을 확인하고 `export_hailo8.py` → `compile_saved_har.py`를 차례로 실행하는 초기 스크립트. **마지막 단계가 수준 0**이므로 현재의 성공 경로는 아래의 단계별 명령이다. |
| `best_11s_hailo_model/metadata.yaml` | Ultralytics 내보내기가 자동 생성한 모델 설명. 작업 종류, 입력 크기, 클래스, Hailo 아키텍처를 기록한다. |
| `best_11s_hailo_model/best_11s.hef` | Hailo-8에서 실행할 최종 INT8 모델. `compile_saved_har_max.py`가 컴파일에 성공하면 이 경로에 저장한다. |
| `acceleras.log`, `allocator.log`, `hailo_sdk.client.log`, `hailo_sdk.core.log` | DFC 실행 중 자동 생성한 진단 로그. 오류 분석용이며 추론에 필요한 파일은 아니다. `allocator.log`는 비어 있을 수 있다. |
| `.gitignore` | 용량이 큰 체크포인트·HAR·ONNX와 로그를 Git 변경 목록에서 제외한다. HEF는 제외하지 않는다. |
| `README.md` | 이 변환 절차와 실행 방법을 설명한다. |

`export_hailo8.py`는 Ultralytics의 Hailo 내보내기를 호출한다. WSL 메모리 부족을 피하려고 DFC 모델 스크립트의 양자화 후 파인튜닝을 끄고 최적화 수준을 0으로 바꾼다. HEF 컴파일 함수는 임시로 HAR 저장 함수로 대체한다. Ultralytics가 요구하는 131,072바이트 임시 HEF는 내보내기 반환 후 삭제한다. 따라서 **1단계의 임시 HEF는 배포 파일이 아니다.** Ultralytics가 사용한 임시 ONNX도 내보내기 후 남아 있지 않다.

두 컴파일 Python 파일은 모두 `ClientRunner(hw_arch="hailo8", har=...)`로 저장된 HAR를 읽는다. HAR 최적화와 HEF 컴파일을 서로 다른 Python 프로세스에서 실행해 최대 메모리 사용을 줄인다. 컴파일 결과는 먼저 `.hef.tmp`에 쓰고 완료되면 `.hef`로 바꾼다. `model_script.alls`의 **모델 최적화 수준 0**과 `compile_saved_har_max.py`의 **컴파일 탐색 수준 `max`**는 서로 다른 설정이다.

## HEF를 다시 생성하는 명령

아래 PowerShell 명령은 **프로젝트 루트** `C:\Users\c\Desktop\대학생활\we_meet_ROS2`에서 실행한다. 이미 존재하는 최적화 HAR에서 HEF만 다시 만들 때는 이 명령 하나를 사용한다. 완료되면 기존 `best_11s.hef`를 새 결과로 교체한다.

```powershell
wsl.exe -d Ubuntu-22.04 -- /root/.venvs/we_meet_hailo8/bin/python /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s/compile_saved_har_max.py
```

체크포인트부터 전체 변환을 다시 해야 할 때는 다음 순서로 실행한다. **1단계 내보내기는 같은 출력 경로의 기존 HEF와 HAR를 교체할 수 있으므로 필요한 결과물을 먼저 별도로 보관한다.** 데이터셋 경로가 바뀌었다면 `calibration_data.yaml`과 `calibration_images.txt`를 먼저 수정한다.

```powershell
wsl.exe -d Ubuntu-22.04 -- /root/.venvs/we_meet_hailo8/bin/python /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s/export_hailo8.py
wsl.exe -d Ubuntu-22.04 -- /root/.venvs/we_meet_hailo8/bin/python /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/hef_11s/compile_saved_har_max.py
```

전체 1,131장을 1280px float32 배열로 한꺼번에 적재하면 약 **20.7GiB의 임시 RAM**이 필요해 첫 시도가 실패했다. 이후 128장과 최적화 수준 2에서도 WSL 메모리 부족이 발생해 64장과 수준 0을 사용했다. 이는 **HEF 파일 크기가 아니다.** 64장은 [Ultralytics Hailo 가이드](https://docs.ultralytics.com/integrations/hailo)의 정확도 권장 보정 이미지 수보다 적다. 실제 데이터에서 원본 `.pt`와 HEF의 검출·마스크 정확도를 비교해야 한다.

## Hailo 장치에서 HEF 실행 및 FPS 확인

**아래 명령은 Hailo-8 장치와 호환 HailoRT가 설치된 대상 컴퓨터에서 실행한다.** WSL 컴파일 환경에 Hailo 장치가 없으면 추론·FPS는 측정할 수 없다. `best_11s_hailo_model` 폴더 전체를 대상 컴퓨터로 복사하고, 다음 예시의 `/path/to/...`를 실제 경로로 바꾼다. 다른 장치를 쓴다면 HEF 아키텍처가 장치와 일치하는지 먼저 확인한다.

```bash
hailortcli fw-control identify
hailortcli parse-hef /path/to/best_11s_hailo_model/best_11s.hef
hailortcli benchmark /path/to/best_11s_hailo_model/best_11s.hef
```

`benchmark`는 Hailo 추론 자체의 처리량을 보는 명령이다. 카메라 입력, 1280 리사이즈, 분할 후처리, 화면 표시까지 포함한 **전체 응용 프로그램 FPS와는 다르다.** [Ultralytics Hailo 가이드](https://docs.ultralytics.com/integrations/hailo)도 장치 추론과 전체 파이프라인을 나누어 측정하도록 안내한다.

대상 컴퓨터에 HailoRT와 Hailo 지원 Ultralytics가 설치돼 있으면, HEF와 `metadata.yaml`이 함께 든 **폴더를 모델 경로**로 지정해 이미지 또는 영상을 추론할 수 있다.

```bash
yolo predict task=segment model=/path/to/best_11s_hailo_model source=/path/to/image.jpg imgsz=1280
yolo predict task=segment model=/path/to/best_11s_hailo_model source=/path/to/video.mp4 imgsz=1280
```

정확도 검증용 데이터셋도 대상 컴퓨터에 있을 때:

```bash
yolo val task=segment model=/path/to/best_11s_hailo_model data=/path/to/dataset_11s_seg/data.yaml imgsz=1280
```

YOLO11 분할 HEF는 원시 출력 텐서를 내며 Ultralytics가 박스·마스크 후처리를 수행한다. 직접 HailoRT 프로그램을 작성한다면 같은 후처리가 필요하다. 이 저장소의 `../run_target_detection.sh`와 `../tools/run_target_detection.py`는 현재 기본값으로 `.pt`를 사용하는 Gazebo 시뮬레이션 경로이며, 위 HEF 장치 추론 명령과는 별개다.

## 실행 기록

- 1280×1280 ONNX 변환과 HAR 최적화는 완료됐다. 임시 ONNX는 내보내기 이후 삭제됐다.
- 컴파일 탐색 수준 0에서는 단일 컨텍스트 배치에 실패했고, 여러 컨텍스트 배치 탐색도 시간 초과로 끝났다.
- `compiler_optimization_level=max`로 다시 컴파일한 뒤 현재의 26,443,818바이트 HEF가 생성됐다. 파일 무결성은 위 SHA-256으로 확인할 수 있다.
