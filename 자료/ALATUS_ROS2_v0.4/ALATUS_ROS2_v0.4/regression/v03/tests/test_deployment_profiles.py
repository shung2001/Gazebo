"""Validate the generated JSON-scalar subset of ROS YAML against the executable schema."""
import json
from pathlib import Path
import unittest
from alatus_runtime.parameter_specs import SPECS
from alatus_runtime.parameters import validate

ROOT=Path(__file__).resolve().parents[1]

def read_profile(path):
    data={}
    current=None
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'): continue
        if not line.startswith(' '):
            if not line.endswith(':'): raise ValueError('Invalid node key')
            current=line[:-1]; data[current]={}
        elif line=='  ros__parameters:':
            continue
        elif line.startswith('    ') and ': ' in line:
            name,value=line.strip().split(': ',1)
            if name in data[current]: raise ValueError('Duplicate parameter')
            data[current][name]=json.loads(value)
        else: raise ValueError('Unexpected generated-profile syntax')
    return data

class DeploymentProfileTests(unittest.TestCase):
    def test_every_profile_valid(self):
        for path in [ROOT/'src/alatus_bringup/config/shadow.yaml',ROOT/'src/alatus_bringup/config/onboard_observer.yaml',ROOT/'deploy/onboard.yaml']:
            for node,parameters in read_profile(path).items():
                self.assertFalse(parameters.pop('use_sim_time'))
                validate(node,parameters)

    def test_onboard_has_no_mock_sources(self):
        onboard=read_profile(ROOT/'deploy/onboard.yaml')
        self.assertNotIn('mock_perception',onboard);self.assertNotIn('mock_status',onboard)
        for node in ['mission','guidance','safety_gate']:
            self.assertEqual(onboard[node]['expected_status_source'],'PX4_VEHICLE_STATUS_ONLY')
        self.assertFalse(onboard['px4_status']['contract_reviewed'])

    def test_docker_includes_test_inputs_and_shells(self):
        docker=(ROOT/'deploy/Dockerfile').read_text()
        for folder in ['src','tests','tools','design','docs','deploy']:
            self.assertIn('COPY '+folder+'/',docker)
        # Files are extracted on Linux too: CRLF would break the shebang/exec path.
        for path in (ROOT/'deploy/entrypoint.sh',ROOT/'tools/validate_humble.sh'):
            self.assertNotIn(b'\r\n',path.read_bytes())

    def test_consumer_contracts_match_profiles(self):
        for path in [ROOT/'src/alatus_bringup/config/shadow.yaml',ROOT/'deploy/onboard.yaml']:
            profile=read_profile(path)
            frame=profile['tracker']['optical_frame_id']
            for name in ['mission','guidance','safety_gate']:
                self.assertEqual(profile[name]['optical_frame_id'],frame)
                self.assertEqual(profile[name]['expected_status_source'],profile['mission']['expected_status_source'])
            for name in ['mission','guidance']:
                self.assertEqual(profile[name]['min_confidence'],profile['tracker']['min_confidence'])
            self.assertEqual(profile['guidance']['correction_limit_norm'],profile['safety_gate']['correction_limit_norm'])
