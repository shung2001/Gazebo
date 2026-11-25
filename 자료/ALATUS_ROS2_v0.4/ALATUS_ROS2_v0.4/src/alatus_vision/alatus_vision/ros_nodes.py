"""One estimation/mission/guidance node; unchanged v0.3 pure Mission and clock guard."""
import time,math,yaml
import numpy as np
import rclpy
from .configuration import validate
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data
from std_srvs.srv import SetBool
from alatus_interfaces.msg import (DetectionFrame,TrackEstimate,AircraftState,VisualCommand,
    TargetTrack,MissionState,GuidanceProposal,SafetyStatus,AircraftStatus)
from alatus_runtime.core import Mission
from alatus_runtime.clock_guard import ClockGuard
from .tracking import KalmanTracker,Detection
from .guidance import Guidance

def sec(s):return s.sec+s.nanosec*1e-9

def stamp(t):
    from builtin_interfaces.msg import Time
    n=round(max(0.,t)*1e9);return Time(sec=n//10**9,nanosec=n%10**9)

class Pipeline(Node):
    def __init__(self):
        super().__init__('vision_pipeline')
        path=self.declare_parameter('config_path','').value
        self.c=validate(yaml.safe_load(open(path)));c=self.c
        self.filter=KalmanTracker(class_id=c['class_id'],confidence=c['confidence'],**c['filter'])
        self.controller=Guidance(c);self.mission=Mission();self.guard=ClockGuard()
        self.state=None;self.receipt=-math.inf;self.last_tick=None;self.last_id=None;self.last_mode=None
        self.input_receipt=-math.inf;self.state_dict={};self.clock_fault=False
        self.pubs={name:self.create_publisher(kind,'/alatus/'+name,10) for name,kind in [
            ('track_estimate',TrackEstimate),('target_track',TargetTrack),('mission_state',MissionState),
            ('visual_command',VisualCommand),('guidance_proposal',GuidanceProposal),('safety_status',SafetyStatus)]}
        self.create_subscription(DetectionFrame,'/alatus/detection_frame',self.detect,10)
        if not c['mock_aircraft']:
            self.create_subscription(AircraftState,'/alatus/aircraft_state',self.aircraft,qos_profile_sensor_data)
        else:
            self.mock_pub=self.create_publisher(AircraftState,'/alatus/aircraft_state',10)
            self.mock_old=self.create_publisher(AircraftStatus,'/alatus/aircraft_status',10)
        self.create_service(SetBool,'/alatus/shadow_mission',self.request)
        self.create_timer(0.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def now(self):return self.get_clock().now().nanoseconds/1e9
    def request(self,req,res):
        res.success=self.mission.request(req.data) if not self.clock_fault else False
        if not req.data:self.controller.reset()
        res.message='Analysis request only; ABORT requires false then true; clock fault requires restart'
        return res
    def aircraft(self,m):self.state=m;self.receipt=time.monotonic()
    def detect(self,m):
        now=self.now()
        if m.header.frame_id!=self.c['frame_id'] or self.clock_fault:return
        if not math.isfinite(m.inference_latency_s) or m.inference_latency_s<0 or len(m.detections)>64:return
        if len(self.get_publishers_info_by_topic('/alatus/detection_frame'))!=1:return
        ds=[Detection(d.class_id,d.confidence,tuple(d.bbox_xyxy_px)) for d in m.detections]
        before=self.filter.sequence
        self.filter.update(sec(m.header.stamp),int(m.sequence),m.source,int(m.image_width),int(m.image_height),ds,now)
        if self.filter.sequence!=before:self.input_receipt=time.monotonic()
    def mock(self,now):
        m=AircraftState();m.header.stamp=stamp(now);m.header.frame_id='map'
        m.connected=True;m.position_valid=m.attitude_valid=m.velocity_valid=m.airspeed_valid=True
        m.position_enu_m=[0.,0.,30.];m.attitude_xyzw=[0.,0.,0.,1.];m.velocity_enu_m_s=[15.,0.,0.]
        m.airspeed_m_s=15.;m.altitude_local_enu_m=30.;m.source='MOCK_NOT_AIRCRAFT';m.mode='MOCK'
        self.mock_pub.publish(m);self.aircraft(m)
        old=AircraftStatus();old.header=m.header;old.status_received=True;old.source=m.source;self.mock_old.publish(old)
    def tick(self):
        now=self.now();wall=time.monotonic();c=self.c
        self.clock_fault=not self.guard.update(now,wall,self.get_parameter('use_sim_time').value)
        if self.clock_fault:self.filter.reset();self.mission.state='ABORT';self.controller.reset()
        if c['mock_aircraft']:self.mock(now)
        s=self.state
        if s is not None and s.mode!=self.last_mode:
            self.controller.reset();self.last_mode=s.mode
        state_ok=(s is not None and 0<=now-sec(s.header.stamp)<=c['input_timeout_s'] and
                  wall-self.receipt<=c['input_timeout_s'] and s.connected and
                  not s.failsafe and not s.manual_override_active and
                  (c['mock_aircraft'] or len(self.get_publishers_info_by_topic('/alatus/aircraft_state'))==1))
        snap=self.filter.snapshot(now)
        if snap:
            snap['dimensions']=self.filter.dimensions
            snap['valid']=snap['valid'] and wall-self.input_receipt<=c['input_timeout_s'] and not self.clock_fault
        target_ok=bool(snap and snap['valid'])
        state=self.mission.step(target_ok,state_ok and not self.clock_fault)
        allowed=state=='TRACK_SHADOW' and target_ok
        dt=0.05 if self.last_tick is None else now-self.last_tick;self.last_tick=now
        if snap and self.last_id!=snap['track_id']:
            self.controller.reset();self.last_id=snap['track_id']
        sd={} if s is None else dict(connected=state_ok,position_valid=s.position_valid,
            attitude_valid=s.attitude_valid,velocity_valid=s.velocity_valid,airspeed_valid=s.airspeed_valid,
            position=list(s.position_enu_m),velocity=list(s.velocity_enu_m_s),q=list(s.attitude_xyzw),airspeed=s.airspeed_m_s)
        reviewed=c['source']=='mock' or c.get('controller_reviewed',False)
        result=self.controller.compute(snap,sd,dt,allowed and reviewed)
        if not reviewed:result['reason']='CONTROLLER_REVIEW_REQUIRED'
        tr=TrackEstimate();tr.header.stamp=stamp(now);tr.header.frame_id=c['frame_id']
        old=TargetTrack();old.header.stamp=stamp(0.);old.header.frame_id=c['frame_id']
        if snap:
            tr.valid=snap['valid'];tr.observation_stamp=stamp(snap['stamp']);tr.track_id=snap['track_id']
            tr.image_width,tr.image_height=snap['dimensions'];tr.state_px=list(map(float,snap['x']))
            tr.covariance=list(map(float,snap['P'].ravel()));tr.prediction_age_s=snap['age'];tr.state=snap['state'];tr.source=self.filter.source
            old.header.stamp=tr.observation_stamp;old.valid=tr.valid;old.track_id=tr.track_id
            old.center_x_norm=float(snap['x'][0]/tr.image_width);old.center_y_norm=float(snap['x'][1]/tr.image_height)
            old.confidence=float(snap['confidence']);old.consecutive_hits=self.filter.hits
            old.valid=old.valid and 0<=old.center_x_norm<=1 and 0<=old.center_y_norm<=1
        else:tr.state='LOST'
        ms=MissionState();ms.header.stamp=stamp(now);ms.state=state;ms.proposal_allowed=allowed;ms.reason='V04_ANALYSIS_ONLY'
        cmd=VisualCommand();cmd.header.stamp=stamp(now);cmd.header.frame_id='map';cmd.shadow_only=True
        cmd.valid=result['valid'];cmd.reason=result['reason'];cmd.mode='POSITION_LOCAL_ENU'
        cmd.observation_stamp=tr.observation_stamp
        if cmd.valid:
            cmd.bearing_error_rad=result['bearing_error'];cmd.elevation_rad=result['elevation']
            cmd.course_rate_rad_s=result['course_rate'];cmd.bank_diagnostic_rad=result['bank']
            cmd.flight_path_angle_rad=result['gamma'];cmd.position_enu_m=result['target'];cmd.saturated=result['saturated']
        gp=GuidanceProposal();gp.header=tr.header;gp.observation_stamp=tr.observation_stamp;gp.shadow_only=True
        gp.valid=cmd.valid;gp.reason=cmd.reason
        if snap:gp.image_error_x=old.center_x_norm-0.5;gp.image_error_y=old.center_y_norm-0.5
        safety=SafetyStatus();safety.header.stamp=stamp(now);safety.inputs_valid=cmd.valid;safety.control_allowed=False
        safety.reason='SHADOW_IMMUTABLE_DENY;SITL_SENDER_HAS_SEPARATE_PERMIT'
        for name,msg in [('track_estimate',tr),('target_track',old),('mission_state',ms),('visual_command',cmd),('guidance_proposal',gp),('safety_status',safety)]:self.pubs[name].publish(msg)

def spin(kind,args=None):
    rclpy.init(args=args);node=None
    try:node=kind();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()

def pipeline_main(args=None):spin(Pipeline,args)
