# 01. v0.3 → v0.4

## 1. 이번 단계의 목적

원본을 유지하고 신규 경로를 구분한다. v0.3 실행 성공이 v0.4 제어 성공을 뜻하지 않는다.

## 2. 필요한 사전조건

제공 ZIP을 내려받는다. ~/PX4-Autopilot v1.16은 건드리지 않는다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

```bash
mkdir -p ~/Desktop/INHA-ALATUS_SW
unzip ~/Downloads/ALATUS_ROS2_v0.4.zip -d ~/Desktop/INHA-ALATUS_SW
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
sudo apt update
sudo apt install -y git python3-pytest python3-numpy python3-yaml
bash tools/test_v04.sh
code .
```

원본 비교:

```bash
diff src/alatus_runtime/alatus_runtime/core.py regression/v03/src/alatus_runtime/alatus_runtime/core.py
diff src/alatus_interfaces/msg/MissionState.msg regression/v03/src/alatus_interfaces/msg/MissionState.msg
```

## 5. 전체 코드 또는 수정파일

전체 원본: regression/v03. 변경목록: docs/V04_CHANGELOG_KO.md. 신규 수학: src/alatus_vision/alatus_vision/*.py. 기존 코드는 같은 패키지에 남겼다.

## 6. 예상 출력

pytest와 unittest 결과가 실제로 PASS해야 한다. diff는 차이 없이 종료한다. 제공자 실행환경은 Python 3.12이며 사용자 Jammy 3.10은 별도 검증 대상이다.

## 7. 성공 판정

파일 보존 검사, 신규 시험, 기존 40개 회귀시험이 함께 통과한다.

## 8. 대표적인 오류

ZIP 폴더가 한 단계 중첩되거나 pytest/numpy를 찾지 못함.

## 9. 오류 해결 방법

pwd와 ls로 README.md 및 src가 바로 보이는 루트인지 확인한다. 필요한 apt 패키지를 설치한다. 다른 v0.3 install overlay를 source한 터미널 대신 새 터미널을 사용한다.

## 10. 다음 단계와 연결

02에서 새 작업공간을 빌드한다. ROS 없이 이 단계만 통과하면 Level 1 일부 검증이다.
