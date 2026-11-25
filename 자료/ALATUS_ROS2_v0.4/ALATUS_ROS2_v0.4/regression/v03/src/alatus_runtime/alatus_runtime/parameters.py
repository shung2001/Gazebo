"""Pure validation for the actual ROS parameter schema."""
import math
import re
from .parameter_specs import SPECS

def defaults(node):
    return {name: spec['default'] for name,spec in SPECS[node].items()}

def validate(node, values):
    expected=SPECS[node]
    if set(values)!=set(expected):
        raise ValueError('Parameter keys do not match '+node)
    types={'bool':bool,'int64':int,'float64':float,'string':str}
    for name,spec in expected.items():
        value=values[name]
        if type(value) is not types[spec['type']]:
            raise ValueError(name+': wrong parameter type')
        if type(value) is float and not math.isfinite(value):
            raise ValueError(name+': must be finite')
        bounds=spec['bounds']
        if bounds and not bounds[0]<=value<=bounds[1]:
            raise ValueError(name+': outside '+str(bounds))
        if name in ['optical_frame_id','socket_path','target_class_id','status_topic','expected_status_source']:
            if not value or any(c.isspace() for c in value):
                raise ValueError(name+': must be nonempty and contain no whitespace')
        if name=='status_topic' and not value.startswith('/fmu/out/'):
            raise ValueError('status_topic: only /fmu/out/ read-only telemetry is accepted')
        if name=='socket_path' and (not value.startswith('/') or len(value.encode())>100):
            raise ValueError('socket_path: require short absolute Linux path')
        if name=='expected_status_source' and value not in ['MOCK_NOT_AIRCRAFT','PX4_VEHICLE_STATUS_ONLY']:
            raise ValueError('expected_status_source: unsupported source')
        if name.endswith('_commit_sha') and value and not re.fullmatch('[0-9a-fA-F]{40}',value):
            raise ValueError(name+': require a full 40-character git SHA')
    if node=='mock_perception':
        x,a=values['center_x_norm'],values['amplitude_x_norm']
        if x-a<0 or x+a>1: raise ValueError('centre +/- amplitude must remain in [0,1]')
    if node=='tracker' and values['max_observation_gap_s']>values['detection_max_age_s']:
        raise ValueError('observation gap exceeds detection age')
    if 'publish_rate_hz' in values:
        period=1.0/values['publish_rate_hz']
        for name,value in values.items():
            if name.endswith('_max_age_s') or name=='max_input_age_s':
                if value<=period: raise ValueError(name+': must exceed timer period')
    return dict(values)
