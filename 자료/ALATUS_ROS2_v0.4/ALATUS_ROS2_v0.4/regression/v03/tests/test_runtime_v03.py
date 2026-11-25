import copy
import json
import math
from pathlib import Path
import sys
import unittest
from alatus_runtime.parameter_specs import SPECS
from alatus_runtime.parameters import defaults,validate
from alatus_runtime.core import Tracker,proposal,gate
from alatus_runtime.clock_guard import ClockGuard
from alatus_runtime.perception_protocol import Receiver

class ParameterTests(unittest.TestCase):
    def test_all_defaults_valid(self):
        for node in SPECS: self.assertEqual(validate(node,defaults(node)),defaults(node))

    def test_all_numeric_boundaries_and_nonfinite(self):
        for node,params in SPECS.items():
            for name,spec in params.items():
                if spec['type'] not in ['int64','float64']: continue
                for bad in [True,'0']+([math.nan,math.inf,-math.inf] if spec['type']=='float64' else [0.5]):
                    values=defaults(node); values[name]=bad
                    with self.assertRaises(ValueError,msg=node+'.'+name): validate(node,values)
                if spec['bounds']:
                    lo,hi=spec['bounds']
                    for bad in [lo-1,hi+1]:
                        values=defaults(node); values[name]=float(bad) if spec['type']=='float64' else int(bad)
                        with self.assertRaises(ValueError,msg=node+'.'+name): validate(node,values)

    def test_coupled_constraints(self):
        for node,changes in [('mock_perception',{'center_x_norm':0.1,'amplitude_x_norm':0.2}),
                             ('tracker',{'detection_max_age_s':0.2,'max_observation_gap_s':0.5}),
                             ('mission',{'publish_rate_hz':1.0,'status_max_age_s':0.5})]:
            values=defaults(node);values.update(changes)
            with self.assertRaises(ValueError):validate(node,values)

    def test_string_and_provenance_constraints(self):
        for node,name,bad in [('tracker','optical_frame_id',''),('mission','expected_status_source','ANY'),
                              ('px4_status','status_topic','/fmu/in/anything'),('px4_status','firmware_commit_sha','main'),
                              ('perception_socket','socket_path','relative.sock')]:
            values=defaults(node);values[name]=bad
            with self.assertRaises(ValueError):validate(node,values)

    def test_tracker_uses_parameters(self):
        t=Tracker(confirm_hits=2,max_age_s=0.3,max_gap_s=0.2,min_confidence=0.8)
        self.assertFalse(t.update(1,1,True,0.79,.5,.5,1))
        self.assertFalse(t.update(1.1,1.1,True,0.9,.5,.5,1))
        self.assertTrue(t.update(1.2,1.2,True,0.9,.5,.5,1))
        self.assertFalse(t.update(2,1.5,True,0.9,.5,.5,1))

    def test_rejected_future_does_not_poison_tracker(self):
        t=Tracker(confirm_hits=2)
        self.assertFalse(t.update(1,100,True,0.9,.5,.5,1))
        self.assertEqual(t.last_stamp,-1)
        self.assertFalse(t.update(1.1,1.1,True,0.9,.5,.5,1))
        self.assertTrue(t.update(1.2,1.2,True,0.9,.5,.5,1))
        t.reset();self.assertEqual(t.hits,0);self.assertEqual(t.last_stamp,-1)

    def test_guidance_and_gate_use_parameters(self):
        valid,ex,ey,c=proposal(.6,.8,True,.4,.3,1.0,.1)
        self.assertTrue(valid);self.assertAlmostEqual(ex,.2);self.assertAlmostEqual(ey,.5);self.assertEqual(c,-.1)
        self.assertEqual(gate(True,True,True,True,.15,.1),(False,False))
        self.assertEqual(gate(True,True,True,True,.1,.1),(True,False))

    def test_clock_rewind_and_pause_latch(self):
        g=ClockGuard();self.assertTrue(g.update(1,10,False));self.assertFalse(g.update(.9,10.1,False))
        self.assertFalse(g.update(2,10.2,False))
        g=ClockGuard();self.assertTrue(g.update(0,10,True));self.assertFalse(g.update(0,10.6,True))
        g=ClockGuard();self.assertTrue(g.update(1,10,False));self.assertTrue(g.update(1,10.6,False))

def packet():
    return {'schema_version':1,'stream_id':'camera-session-1','sequence':1,'capture_stamp_ns':1000000000,
            'frame_id':'camera_optical','image_width':100,'image_height':100,
            'detections':[{'class_id':'target','confidence':.9,'track_id':7,'bbox_xywh_px':[10,20,20,40]}]}

class ProtocolTests(unittest.TestCase):
    def test_valid_geometry_and_timestamp(self):
        o=Receiver().parse(json.dumps(packet()).encode(),1100000000)
        self.assertTrue(o.valid);self.assertAlmostEqual(o.x,.2);self.assertAlmostEqual(o.y,.4)
        self.assertEqual(o.stamp_ns,1000000000);self.assertEqual(o.target_id,7)

    def test_no_target_is_explicit_invalid(self):
        p=packet();p['detections']=[]
        self.assertFalse(Receiver().parse(json.dumps(p).encode(),1100000000).valid)

    def test_replay_and_new_stream_rejected(self):
        r=Receiver();p=packet();r.parse(json.dumps(p).encode(),1100000000)
        with self.assertRaises(ValueError):r.parse(json.dumps(p).encode(),1100000000)
        p['sequence']=2;p['capture_stamp_ns']=1100000000;p['stream_id']='new'
        with self.assertRaises(ValueError):r.parse(json.dumps(p).encode(),1200000000)

    def test_invalid_packets_do_not_advance_watermark(self):
        r=Receiver();p=packet();p['capture_stamp_ns']=999000000000
        with self.assertRaises(ValueError):r.parse(json.dumps(p).encode(),1100000000)
        self.assertTrue(r.parse(json.dumps(packet()).encode(),1100000000).valid)

    def test_corrupt_schema_bounds_and_ids(self):
        variations=[]
        for key,value in [('frame_id','body'),('image_width',0),('schema_version',True),('capture_stamp_ns',0)]:
            p=packet();p[key]=value;variations.append(p)
        for key,value in [('track_id',None),('track_id',True),('confidence',float('nan')),('bbox_xywh_px',[-1,0,10,10]),('bbox_xywh_px',[90,0,20,20])]:
            p=packet();p['detections'][0][key]=value;variations.append(p)
        for p in variations:
            with self.assertRaises(ValueError):Receiver().parse(json.dumps(p).encode(),1100000000)
        for raw in [b'bad',b'null',b'[]',b'x'*65537]:
            with self.assertRaises(ValueError):Receiver().parse(raw,1100000000)

    def test_class_filter_and_deterministic_selection(self):
        p=packet();p['detections'][0]['class_id']='other'
        self.assertFalse(Receiver().parse(json.dumps(p).encode(),1100000000).valid)
        p=packet();other=copy.deepcopy(p['detections'][0]);other['track_id']=2;p['detections'].append(other)
        self.assertEqual(Receiver().parse(json.dumps(p).encode(),1100000000).target_id,2)

class DeploymentTests(unittest.TestCase):
    def test_onboard_launch_contains_no_mocks(self):
        root=Path(__file__).resolve().parents[1]
        content=(root/'src/alatus_bringup/launch/onboard_observer.launch.py').read_text()
        self.assertNotIn('mock_perception',content);self.assertNotIn('mock_status',content)
        self.assertIn("{'use_sim_time':False}",content)
        compose=(root/'deploy/compose.yaml').read_text()
        self.assertNotIn('privileged:',compose);self.assertIn('read_only: true',compose)
        self.assertIn('linux/arm64',compose)
