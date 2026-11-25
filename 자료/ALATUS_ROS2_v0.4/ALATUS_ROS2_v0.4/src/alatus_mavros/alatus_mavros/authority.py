"""Independent SITL-only permission validation; a review record, not hardware attestation."""
from pathlib import Path
import math,re
import numpy as np

def validate_permit(p):
    flags=['enable','simulation_only','interface_reviewed','failsafe_reviewed','manual_mode_switch_reviewed']
    if not all(p.get(k) is True for k in flags):raise ValueError('SITL permit incomplete')
    if p.get('interface')!='POSITION_LOCAL_ENU':raise ValueError('Unsupported command interface')
    if not re.fullmatch(r'[0-9a-f]{40}',p.get('px4_commit','')):raise ValueError('Pinned PX4 commit required')
    if not p.get('mavros_version') or p['mavros_version']=='TBD':raise ValueError('MAVROS version required')
    if p.get('fcu_url')!='udp://:14540@127.0.0.1:14557':raise ValueError('Only dedicated local SITL URL permitted')
    limits=['minimum_airspeed_m_s','minimum_altitude_enu_m','maximum_altitude_enu_m','maximum_bank_rad','maximum_pitch_rad','maximum_target_distance_m']
    if any(type(p.get(k)) not in [int,float] or not math.isfinite(p[k]) for k in limits):raise ValueError('Reviewed numeric limits required')
    if p['minimum_airspeed_m_s']<=0 or not 0<p['maximum_bank_rad']<math.pi/2 or not 0<p['maximum_pitch_rad']<math.pi/2 or p['minimum_altitude_enu_m']>=p['maximum_altitude_enu_m'] or p['maximum_target_distance_m']<=0:raise ValueError('Invalid permit limits')
    paths=p.get('evidence_paths',[])
    if not paths or any(not Path(x).is_file() for x in paths):raise ValueError('Review evidence files required')
    return True

def local_sitl(pid):
    try:
        exe=Path('/proc')/str(int(pid))/'exe'
        return str(exe.resolve(strict=True)).endswith('/build/px4_sitl_default/bin/px4')
    except (ValueError,OSError):return False

def eligible(p,state,command,track,mission,now,receipt_age):
    if receipt_age>.25 or not 0<=now-state['stamp']<=.25 or not 0<=now-command['stamp']<=.25:return False,'STALE_STATE_OR_COMMAND'
    if not 0<=now-command['observation_stamp']<=.1:return False,'STALE_MEASUREMENT'
    if not command['valid'] or mission!='TRACK_SHADOW' or not track:return False,'MISSION_OR_TARGET_INVALID'
    if state['source']!='MAVROS' or not all(state[k] for k in ['connected','armed','position_valid','attitude_valid','velocity_valid','airspeed_valid']):return False,'AIRCRAFT_INVALID'
    if state['failsafe'] or state['manual_override_active'] or state['mode'] not in ['AUTO.LOITER','OFFBOARD']:return False,'PX4_MODE_OR_FAULT'
    if not all(math.isfinite(x) for x in [*state['position'],*state['q'],state['airspeed'],*command['target']]):return False,'NONFINITE'
    if abs(sum(x*x for x in state['q'])-1)>.02:return False,'ATTITUDE_INVALID'
    if state['airspeed']<p['minimum_airspeed_m_s']:return False,'AIRSPEED'
    if not p['minimum_altitude_enu_m']<=state['position'][2]<=p['maximum_altitude_enu_m']:return False,'ALTITUDE'
    x,y,z,w=state['q'];roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y));pitch=math.asin(max(-1,min(1,2*(w*y-z*x))))
    if abs(roll)>p['maximum_bank_rad'] or abs(pitch)>p['maximum_pitch_rad']:return False,'ATTITUDE_ENVELOPE'
    if not p['minimum_altitude_enu_m']<=command['target'][2]<=p['maximum_altitude_enu_m']:return False,'TARGET_ALTITUDE'
    if np.linalg.norm(np.array(command['target'])-state['position'])>p['maximum_target_distance_m']:return False,'TARGET_DISTANCE'
    return True,'SITL_POSITION_STREAM_ONLY'
