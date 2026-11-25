# PD/PID 구현과 튜닝

pid.py는 실제 dt를 사용한다. 최초 derivative=0, derivative_tau의 1차 필터, 출력 Saturation, Slew Limit, 조건부 적분 Anti-windup을 구현했다. NaN/Inf/비양수 dt/긴 dt/Disable에서 내부 적분·출력·미분 상태를 모두 초기화한다. Target Lost, Mission Stop, Track ID 변화, Clock fault에도 상위 Pipeline이 reset한다. 의미 있는 Setpoint 변경은 reset=True 또는 상위 reset을 사용한다.

Lateral 단위: error rad, output rad/s. Kp 단위 1/s, Ki 1/s², Kd 무차원이다. Vertical 단위: error rad, output gamma rad. Kp 무차원, Ki 1/s, Kd s다. limit은 출력 단위, slew는 출력 단위/s다. D filter tau는 s다. 적분 limit은 error*s 단위다.

기본 실환경 YAML의 Gain과 Limit은 0, Calibration은 null/false다. 실제 기체용 확정값이 아니다. Mock YAML의 숫자는 합성 입력을 시험하기 위한 Fixture다. 실환경에서 controller_reviewed=true를 만들기 전에 모든 Gain/속도/Lookahead/고도/Bank/Slew를 검토한다.

수치미분은 error wrap 경계와 노이즈에 민감하다. PID API의 rate 인자는 독립 추정 error rate를 받을 수 있지만 현재 Guidance는 수치미분을 사용한다. 영상 KF의 u_dot를 그대로 course error derivative에 넣으면 카메라 회전과 투영 미분을 무시하므로 잘못이다. 추후 Jacobian 및 자세 각속도를 포함해 보정한 Bearing Rate를 공급할 수 있다. 큰 Setpoint 변경과 +-pi wrap에서는 reset과 접근영역 제한이 필요하다.

## SITL 튜닝 순서

1. 공식 기체 기본 비행과 PX4 내부 튜닝이 먼저 정상이어야 한다.
2. Shadow에서 Intrinsics/Extrinsics와 좌우·상하 부호부터 확인한다.
3. Ki=Kd=0으로 시작하고 낮은 외부 Kp에서 경로 응답을 기록한다. 여기서 특정 숫자를 비행용으로 제시하지 않는다.
4. 동일 초기조건에서 작은 표적 Bearing Step을 주고 rise/settling/overshoot/saturation을 비교한다.
5. Kd를 추가하며 감쇠와 노이즈/추론 지연 민감도를 확인한다.
6. 지속 Bias가 실측될 때만 Ki를 검토하고 Anti-windup/Mode reset을 재시험한다.
7. 여러 Ground/Airspeed, Crosswind, Occlusion, artificial delay 조건을 비교한다.
8. PX4 ULog 및 ROS Bag로 실제 궤적/상태/외부 목표를 함께 분석한다.

출력이 제한 안에 있다는 시험은 항공기의 안정성 증명이 아니다. Slew와 Bank diagnostic 제한도 PX4 실제 응답을 보장하지 않는다. 시험한 모델과 운용영역별 결과를 따로 저장한다.
