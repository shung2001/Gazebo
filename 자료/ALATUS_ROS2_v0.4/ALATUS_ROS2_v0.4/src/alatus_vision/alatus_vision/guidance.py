"""Experimental bearing-to-course lookahead, not net interception guidance.
Lateral PID: ENU course error rad -> ENU course rate rad/s (CCW).
Longitudinal PID: world LOS elevation rad -> desired flight path angle rad.
PX4 receives ONLY position; its NPFG/TECS decide actual bank/pitch/thrust.
"""
import math
import numpy as np
from .pid import PID,PIDConfig
from .geometry import bearing,wrap,rotation

class Guidance:
    def __init__(self,cfg):
        self.c=cfg
        self.lat=PID(PIDConfig(**cfg['lateral_pid']));self.vert=PID(PIDConfig(**cfg['vertical_pid']))
    def reset(self):self.lat.reset();self.vert.reset()
    def compute(self,track,state,dt,enabled):
        c=self.c
        if not enabled or not track or not track['valid'] or track['age']>c['command_measurement_age_s']:
            self.reset();return {'valid':False,'reason':'DISABLED_OR_TARGET_LOST'}
        try:
            required=['connected','position_valid','attitude_valid','velocity_valid','airspeed_valid']
            if not all(state.get(k,False) for k in required):raise ValueError('AIRCRAFT_STATE_INVALID')
            vals=[*state['position'],*state['velocity'],*state['q'],state['airspeed']]
            if not all(math.isfinite(v) for v in vals):raise ValueError('NONFINITE_AIRCRAFT_STATE')
            if not 0<dt<=0.5:raise ValueError('INVALID_DT')
            if state['airspeed']<c['min_airspeed_m_s']:raise ValueError('INSUFFICIENT_AIRSPEED')
            vel=state['velocity'];speed=math.hypot(vel[0],vel[1])
            if speed<c['min_groundspeed_m_s']:raise ValueError('INSUFFICIENT_GROUNDSPEED')
            az,el,_=bearing(track['x'][0],track['x'][1],c['camera'],*track['dimensions'],state['q'])
            course=math.atan2(vel[1],vel[0]);err=wrap(az-course)
            rate,sat=self.lat.step(err,dt)
            gamma,sat_v=self.vert.step(el,dt)
            max_rate=9.80665*math.tan(c['bank_limit_rad'])/speed
            limited=max(-max_rate,min(max_rate,rate));sat=sat or limited!=rate
            desired=course+limited*c['course_horizon_s']
            L=c['lookahead_m'];pos=state['position']
            z=pos[2]+L*math.tan(gamma)
            z=max(c['altitude_floor_enu_m'],min(c['altitude_ceiling_enu_m'],z))
            # Positive right-wing-down bank corresponds to negative ENU course rate.
            bank=-math.atan2(speed*limited,9.80665)
            target=[pos[0]+L*math.cos(desired),pos[1]+L*math.sin(desired),z]
            if not np.isfinite(target).all():raise ValueError('NONFINITE_COMMAND')
            return dict(valid=True,reason='EXPERIMENTAL_BEARING_FOLLOW_NOT_NET_CAPTURE',
                        target=target,bearing_error=err,elevation=el,course_rate=limited,
                        bank=bank,gamma=gamma,saturated=sat or sat_v)
        except (ValueError,KeyError,TypeError) as e:
            self.reset();return dict(valid=False,reason=str(e))
