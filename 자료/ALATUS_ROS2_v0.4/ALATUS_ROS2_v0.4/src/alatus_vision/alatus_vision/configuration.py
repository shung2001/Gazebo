"""Fail early for reviewed configurations that still contain invalid limits."""
import math

def validate(c):
    if c.get('schema_version')!=4:raise ValueError('Expected v0.4 configuration')
    if c.get('source') not in ['mock','video','image','socket']:raise ValueError('Unknown input source')
    if not 0<c['confidence']<=1 or c['input_timeout_s']<=0:raise ValueError('Invalid confidence/timeout')
    if c.get('mock_aircraft') and c.get('environment')=='sitl':raise ValueError('SITL must use MAVROS state')
    if c.get('controller_reviewed'):
        keys=['min_airspeed_m_s','min_groundspeed_m_s','bank_limit_rad','course_horizon_s','lookahead_m']
        if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) or c[k]<=0 for k in keys):raise ValueError('Reviewed controller needs positive finite limits')
        if not c['camera']['calibrated'] or not 0<c['bank_limit_rad']<math.pi/2 or c['altitude_floor_enu_m']>=c['altitude_ceiling_enu_m']:raise ValueError('Reviewed geometry/envelope invalid')
    return c
