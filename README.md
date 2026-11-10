# QGIS Scene.obj → Gazebo 캠퍼스 환경

`QGIS/Scene.obj`를 Gazebo Harmonic 8.15.0의 건물 환경으로 구성하고, 키보드로 조종하는 VTOL을 추가했다. 원본 OBJ·MTL·SHP·QGIS 프로젝트는 수정하지 않았다.

**기본 실행 명령을 VTOL 포함 환경으로 변경했다.** 아래 `run_vtol.sh`가 캠퍼스·VTOL·조종 창을 함께 연다. 방향키 설명은 [VTOL 키보드 사용법](VTOL_키보드_사용법.md)에 있다.

## 실행

Ubuntu 22.04 WSL 터미널에서 실행한다. 이미 같은 VTOL 조종 세션이 있으면 기존 조종 창을 먼저 닫는다.

```bash
cd /mnt/c/Users/choih/Desktop/개인_대회/we_meet
bash Gazebo/run_vtol.sh

or 

cd /mnt/c/Users/choih/Desktop/개인_대회/we_meet -> 이 경로는 각자 알아서 환경에 맞게 설정해야함.
bash Gazebo/run_vtol.sh
```

캠퍼스와 VTOL, `VTOL Keyboard Controller` 창이 열린다. 기체는 자동으로 8m 목표 고도까지 이륙한다. 카메라는 기체 좌표계에서 뒤쪽 8m·좌우 0m·위쪽 1m를 따라가므로 기수가 돌아가도 후면 시점을 유지한다. 건물 충돌은 기본 활성화다. 시작 위치는 벽에서 약 14m 떨어진 `(-110,-90,0.6)m`다.

실행기가 모델 검색 경로와 `QT_QPA_PLATFORM=xcb`를 설정하고, 기본 통신 partition으로 `inha_songdo_vtol`을 사용한다.

PowerShell에서 직접 실행할 수도 있다.

```powershell
wsl -d Ubuntu-22.04 -- bash /mnt/c/Users/choih/Desktop/개인_대회/we_meet/Gazebo/run_vtol.sh

or 

wsl -d Ubuntu-22.04 -- bash /mnt/c/Users/c/Desktop/대학생활/we_meet_ROS2/run_vtol.sh
```

## 생성 파일

| 경로 | 역할 |
|---|---|
| `worlds/inha_songdo.sdf` | 지면·조명·시점·시스템 플러그인과 건물을 포함하는 환경 |
| `worlds/inha_songdo_vtol.sdf` | 기본 실행 환경: 캠퍼스 + VTOL |
| `models/inha_songdo_scene/model.sdf` | 움직이지 않는 건물의 visual·collision 정의 |
| `models/inha_songdo_scene/model.config` | 모델 메타데이터 |
| `models/inha_songdo_scene/meshes/scene.obj` | 미터 단위·지역 원점으로 변환한 메시 |
| `models/inha_songdo_scene/meshes/scene.mtl` | 캠퍼스 적색·주변 건물 회색 재질 |
| `scene_metadata.json` | 원본 hash, 변환 배율, 원점, 범위, 좌표 대조 결과 |
| `collision_cells.json`, `models/inha_songdo_scene/meshes/collisions/` | 건물 형상에 맞는 볼록 충돌 영역과 닫힌 STL 조각 |
| `tools/build_qgis_scene.py` | 원본으로부터 위 파일을 재생성하는 Python 도구 |
| `진행과정.md` | 확인·변환·검증 과정과 결과 |

## 좌표와 표현 범위

- 모델 범위는 약 **2,893 × 2,933m**, 최대 상대 높이는 약 **243m**다.
- Gazebo X는 동쪽, Y는 북쪽, Z는 위쪽이다.
- `(0, 0)`은 `인하대_송도캠_찐.shp` 범위의 중심이다. EPSG:5186 좌표로 Easting **169587.889224**, Northing **531717.923926m**에 해당한다.
- Z=0은 원본 OBJ의 최저 높이다. 실측 표고·해발고도나 PX4 고도 기준으로 검증한 값이 아니다.
- 원본 MTL이 비어 있고 UV·텍스처 이미지가 없으므로, QGIS 레이어 스타일을 참고한 단색 재질을 새로 부여했다. 항공사진·도로·수목·실사 외벽 텍스처·DEM은 포함하지 않았다.
- 지면과 건물에 충돌 형상이 있다. 건물은 실제 지붕 삼각형을 바탕으로 만든 **1,529개 볼록 압출 조각**으로 구성해 도시 전체를 하나의 덩어리로 막지 않는다. 기체가 벽·옥상과 물리적으로 접촉하며, 자동 장애물 회피 기능은 아니다.
- VTOL은 `inha_songdo_vtol.sdf`에 추가했다. 과녁·회수망·PX4 SITL·ROS 카메라는 아직 추가하지 않았다.

## 재생성·건물 충돌 옵션

Windows 프로젝트 루트에서는 `python`, Ubuntu에서는 `python3`로 실행한다. 추가 Python 패키지는 필요 없다.

```bash
python3 Gazebo/tools/build_qgis_scene.py
python3 Gazebo/tools/build_keyboard_vtol.py
```

충돌은 기본으로 생성되며, 명시적으로 같은 동작을 선택할 수도 있다.

```bash
python3 Gazebo/tools/build_qgis_scene.py --building-collisions
```

지붕 삼각형의 인접 영역 중 합집합이 볼록한 것만 합쳐 지면까지 채우며, 각 조각은 닫힌 STL로 생성한다. 별도 충돌 형상 덕분에 볼록화로 도시의 빈 공간을 막는 문제와 polyline 압출의 일부 삼각분할 실패를 피한다. 원본 높이 0인 형상은 입체 충돌로 만들지 않는다. 벽·옥상·빈 공간의 대표 시험은 통과했지만, 실제 건물 형상을 측량한 것은 아니다.

시각화 전용 파생본이 필요한 경우에만 `--no-building-collisions`로 생성할 수 있다. 재생성한 뒤에는 `build_keyboard_vtol.py`를 실행하고 월드를 다시 연다. 현재 제공 상태는 충돌 활성화다.

## 캠퍼스만 따로 열기

VTOL 없이 건물만 확인하는 보조 명령은 유지했다.

```bash
bash Gazebo/run_scene.sh
```

이 모드는 `inha_songdo_preview` partition을 사용하고 캠퍼스 전체를 내려다보는 시점으로 시작한다. 기본 사용 명령은 위의 `run_vtol.sh`다.

## 기존 PX4/Gazebo 월드에 추가하기

기존 월드의 `<world>` 안에 아래 모델 include를 넣고, 실행 환경의 `GZ_SIM_RESOURCE_PATH`에 이 폴더의 `models`를 추가한다.

```xml
<include>
  <uri>model://inha_songdo_scene</uri>
</include>
```

예를 들어 현재 프로젝트 경로에서는 다음과 같다.

```bash
export GZ_SIM_RESOURCE_PATH="/mnt/c/Users/choih/Desktop/개인_대회/we_meet/Gazebo/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
```

모델만 기존 월드에 포함하면 기존 조명·지면·시점은 그 월드 설정을 따른다. PX4 기체 spawn 위치와 캠퍼스 지역 원점을 맞춰야 하며, SHP 좌표만으로 PX4 GPS 원점이 자동 설정되지는 않는다. 기본 VTOL 세션에 bridge나 다른 Gazebo 도구를 연결하려면 해당 프로세스에도 다음 값을 적용한다.

```bash
export GZ_PARTITION=inha_songdo_vtol
```

PX4 프로젝트에서 다른 partition을 사용 중이면 해당 값을 유지하고 `run_scene.sh`에도 같은 환경변수를 전달한다.

## 검증

실제 검사한 내용:

- 모델·월드 XML 파싱 및 Gazebo `gz sdf -k` 검사 통과.
- SHP 원본 footprint와 OBJ 표본 좌표 대조: 최대 약 **0.026m**, 평균 약 **0.012m** 차이. 이는 입력 파일 간 정합성 검사이며 측량 정확도는 아니다.
- 원본/변환본 정점 **37,950개**, 법선 **37,950개**, 삼각형 **12,650개** 유지.
- Gazebo 서버에서 `inha_songdo` 월드 초기화, GUI의 메시 경로 등록, `gz model --list`의 `ground_plane`·`inha_songdo_scene` 등록 확인.
- VTOL의 실제 물리 비행과 키 이벤트, 3D 화면 캡처를 확인했다. 후면 카메라의 기체 기준 오프셋 `(-8,0,1)m`도 실행 상태에서 확인했다.
- 옥상 위 구체 낙하·건물 밖 구체 낙하·실제 VTOL의 벽 접근 시험이 통과했다. 결과는 `validation/building_collision_acceptance.json`에 있다.
- PX4 비행·ROS 영상·YOLO 추론·실제 환경과의 외관 일치도·충돌 손상 모델은 이번 작업에서 검증하지 않았다.

SDF 검사 명령은 다음과 같다. 독립적인 `gz sdf` 검사기는 Gazebo 런타임의 검색 변수와 별도로 `SDF_PATH`가 필요하다.

```bash
cd /mnt/c/Users/choih/Desktop/개인_대회/we_meet
SDF_PATH="$PWD/Gazebo/models" gz sdf -k Gazebo/worlds/inha_songdo.sdf
gz sdf -k Gazebo/models/inha_songdo_scene/model.sdf
bash -n Gazebo/run_scene.sh
```

구성 방식은 [Gazebo Harmonic SDF worlds](https://gazebosim.org/docs/harmonic/sdf_worlds/)와 [Gazebo의 메시·재질 형식 안내](https://gazebosim.org/api/sim/10/migrationsdf.html)를 참고했다.
