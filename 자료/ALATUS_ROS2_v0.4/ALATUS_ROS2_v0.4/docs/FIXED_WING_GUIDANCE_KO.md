# 고정익 유도와 회수 기하

## 좌표계와 부호

OpenCV Optical은 x right / y down / z forward다. ROS Body FLU는 x forward / y left / z up이다. 정면 장착 시험 회전 R=[[0,0,1],[-1,0,0],[0,-1,0]]을 적용하면 우측 표적은 body y<0, 상단 표적은 body z>0이다. World ENU x east/y north/z up이며 Quaternion은 body FLU -> world ENU, xyzw다. MAVROS가 ENU/FLU를 NED/FRD로 바꾼다. ALATUS에서 다시 NED로 바꾸면 이중 변환 오류다.

왜곡 plumb_bob은 cv2.undistortPoints로 제거하고 [x_normalized,y_normalized,1] Ray를 만든다. 회전 행렬 직교성/행렬식과 Quaternion Norm을 검사한다. Calibration/해상도가 맞지 않으면 Invalid다. Camera mounting translation은 LOS 방향 계산 자체에는 필요하지 않지만 Net 교차점 계산에는 필요하다.

## 외부 루프의 출력

1. Optical Ray -> Body FLU -> ENU Ray.
2. azimuth=atan2(ray_north,ray_east), elevation=atan2(ray_up,horizontal).
3. Ground Course=atan2(v_north,v_east). course_error=wrap(azimuth-course).
4. Lateral PD: course_error rad -> course_rate rad/s, ENU 반시계 양수.
5. |course_rate|<=g tan(bank_limit)/groundspeed로 제한.
6. Desired Course=course+rate*course_horizon.
7. Vertical PD: world LOS elevation -> desired flight_path_angle gamma.
8. Lookahead 위치=(east+L cos(course_des), north+L sin(course_des), up+L tan(gamma)).

Bank diagnostic=-atan(V_ground*course_rate/g)이며 right-wing-down 양수 부호를 쓴다. 조화선회·무풍 근사이므로 실제 Bank와 일치한다고 보장하지 않는다. 이 값은 직접 Roll 명령이 아니다. PX4 위치 루프가 자체 속도·경로 오차와 제한을 사용한다. 따라서 외부 bank limit은 실제 PX4 Roll 한계 설정을 대체하지 않는다. PX4의 해당 기체 제한 파라미터도 별도로 검토해야 한다.

Heading 대신 Ground Course를 사용해 실제 지상 이동 방향을 비교하고, 카메라 Ray는 Attitude로 world 방향을 만든다. 횡풍의 Crab은 Heading과 Course가 다르다는 것으로 표현되지만 바람 추정/도달가능성 분석은 별도다. 저속에서 atan2 course가 불안정하므로 Groundspeed 하한을 검사한다. Airspeed 하한은 실속 여유 검토 값이며 현재 실기체 값은 TBD다.

Vertical loop는 영상 위/아래를 즉시 Pitch/Throttle로 취급하지 않는다. World LOS elevation을 제한된 경로각으로 바꾸고 고도 목표를 준다. TECS가 Airspeed/Altitude 에너지를 관리한다. 고도 Floor/Ceiling은 Local ENU 원점 기준이며 AGL/MSL이 아니다. 실제 지형 clearance는 구현하지 않았다. Range/Terrain 정보 없이 급강하 Terminal Guidance를 해서는 안 된다.

## Net Recovery 미완료 경계

과녁 중심에 향하는 Ray와 회수망 중심으로 통과하는 항공기 궤적은 다르다. 실제 Target/Net 중심·간격·Plane normal·카메라 장착 위치·기체 날개폭·회수망 유효영역·접근 경로·허용 충격/속도가 필요하다. 단안 bbox 중심만으로 Range/Time-to-contact/plane orientation을 결정할 수 없다.

geometry.net_intersection은 외부에서 확보한 카메라 world 위치와 Ray, Net Plane, Right/Up basis를 받아 교차점을 계산하는 독립 함수다. Guidance에 자동 연결하지 않았다. 검출 Ray가 Net Plane에 교차하더라도 기체 전체가 포획영역을 통과한다는 뜻은 아니다. 날개폭과 오차/지연/선회 여유로 포획영역을 축소하는 Reachability/Terminal State Planning은 후속 구현이다.

현재 Mission은 IDLE → SEARCH → TRACK_SHADOW이며 status 손실 또는 Tracking 획득 이후 상실은 ABORT로 latch한다. 재획득으로 자동 비행을 재개하지 않는다. stop(false) 후 start(true)로 명시적으로 복구한다. 표적 검색용 정지·제자리 Yaw 명령은 고정익에 구현하지 않는다.
