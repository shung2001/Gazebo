"""Parameterized ROS 2 diagnostics. No aircraft command publishers."""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from std_srvs.srv import SetBool
from alatus_interfaces.msg import (TargetDetection, TargetTrack, AircraftStatus,
                                   MissionState, GuidanceProposal, SafetyStatus)
from .core import Tracker as TrackerLogic, Mission as MissionLogic, fresh, observation_ok, proposal, gate
from .clock_guard import ClockGuard
from .ros_parameters import configure

def seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9

class Base(Node):
    def __init__(self,name):
        super().__init__(name)
        self.config=configure(self,name)
        self._steady_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self._receipts={}
        self._clock_guard=ClockGuard()
        self._clock_bad=False

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def clock_ok(self):
        if not self._clock_guard.update(self.now(),time.monotonic(),self.get_parameter('use_sim_time').value):
            if not self._clock_bad:
                self.get_logger().error('Clock fault latched; restart pipeline')
                if hasattr(self,'logic') and isinstance(self.logic,TrackerLogic): self.logic.reset()
                if hasattr(self,'logic') and isinstance(self.logic,MissionLogic): self.logic.state='ABORT'
            self._clock_bad=True
        return not self._clock_bad

    def timer(self,callback):
        self.create_timer(1.0/self.config['publish_rate_hz'],callback,clock=self._steady_clock)

    def stamp(self,message,frame=''):
        message.header.stamp=self.get_clock().now().to_msg()
        message.header.frame_id=frame
        return message

    def subscribe(self,kind,topic,attribute):
        setattr(self,attribute,None)
        def receive(msg):
            setattr(self,attribute,msg)
            self._receipts[attribute]=time.monotonic()
        self.create_subscription(kind,'/alatus/'+topic,receive,10)

    def current(self,msg,timeout,attribute):
        return (msg is not None and self.clock_ok() and fresh(self.now(),seconds(msg.header.stamp),timeout)
                and fresh(time.monotonic(),self._receipts.get(attribute,float('-inf')),timeout))

    def track_ok(self,msg):
        return (self.current(msg,self.config['track_max_age_s'],'track')
                and msg.header.frame_id==self.config['optical_frame_id']
                and observation_ok(msg.valid,msg.confidence,msg.center_x_norm,msg.center_y_norm,self.config['min_confidence']))

    def status_ok(self,msg):
        return (self.current(msg,self.config['status_max_age_s'],'status') and msg.status_received and not msg.failsafe
                and msg.source==self.config['expected_status_source']
                and len(self.get_publishers_info_by_topic('/alatus/aircraft_status'))==1)

class MockPerception(Base):
    def __init__(self):
        super().__init__('mock_perception')
        self.publisher=self.create_publisher(TargetDetection,'/alatus/detection',10)
        self.timer(self.tick)

    def tick(self):
        p=self.config
        msg=self.stamp(TargetDetection(),p['optical_frame_id'])
        msg.valid=self.clock_ok() and not self.get_parameter('dropout').value
        msg.confidence=p['confidence']
        msg.center_x_norm=p['center_x_norm']+p['amplitude_x_norm']*math.sin(self.now()*p['angular_frequency_rad_s'])
        msg.center_y_norm=p['center_y_norm']
        msg.target_id=p['target_id']
        self.publisher.publish(msg)

class Tracker(Base):
    def __init__(self):
        super().__init__('tracker')
        p=self.config
        self.logic=TrackerLogic(confirm_hits=p['confirm_hits'],max_age_s=p['detection_max_age_s'],
                                max_gap_s=p['max_observation_gap_s'],min_confidence=p['min_confidence'])
        self.last=None
        self.last_receipt=float('-inf')
        self.publisher=self.create_publisher(TargetTrack,'/alatus/target_track',10)
        self.create_subscription(TargetDetection,'/alatus/detection',self.detect,10)
        self.timer(self.tick)

    def detect(self,msg):
        self.last_receipt=time.monotonic()
        out=TargetTrack()
        out.header=msg.header
        out.confidence,out.center_x_norm,out.center_y_norm=msg.confidence,msg.center_x_norm,msg.center_y_norm
        out.track_id=msg.target_id
        acceptable=(self.clock_ok() and msg.header.frame_id==self.config['optical_frame_id']
                    and len(self.get_publishers_info_by_topic('/alatus/detection'))==1)
        out.valid=self.logic.update(self.now(),seconds(msg.header.stamp),msg.valid and acceptable,
                                    msg.confidence,msg.center_x_norm,msg.center_y_norm,msg.target_id)
        out.consecutive_hits=self.logic.hits
        self.last=out

    def tick(self):
        if self.last is None:
            self.clock_ok()
            return
        timeout=self.config['detection_max_age_s']
        if (not self.clock_ok() or not fresh(self.now(),seconds(self.last.header.stamp),timeout)
                or not fresh(time.monotonic(),self.last_receipt,timeout)):
            self.last.valid=False
            self.logic.hits=0
        self.last.consecutive_hits=self.logic.hits
        self.publisher.publish(self.last)

class MockStatus(Base):
    def __init__(self):
        super().__init__('mock_status')
        self.publisher=self.create_publisher(AircraftStatus,'/alatus/aircraft_status',10)
        self.timer(self.tick)

    def tick(self):
        msg=self.stamp(AircraftStatus())
        msg.status_received=self.clock_ok() and self.config['status_received']
        msg.armed=self.config['armed']
        msg.failsafe=self.config['failsafe']
        msg.nav_state=self.config['nav_state']
        msg.source='MOCK_NOT_AIRCRAFT'
        self.publisher.publish(msg)

class Mission(Base):
    def __init__(self):
        super().__init__('mission')
        self.logic=MissionLogic()
        self.subscribe(TargetTrack,'target_track','track')
        self.subscribe(AircraftStatus,'aircraft_status','status')
        self.publisher=self.create_publisher(MissionState,'/alatus/mission_state',10)
        self.create_service(SetBool,'/alatus/shadow_mission',self.request)
        self.timer(self.tick)

    def request(self,req,response):
        if req.data and not self.clock_ok():
            response.success=False
            response.message='Clock fault: restart required'
        else:
            response.success=self.logic.request(req.data)
            response.message='Shadow analysis only; reset ABORT with false before restarting'
        return response

    def tick(self):
        msg=self.stamp(MissionState())
        clock_ok=self.clock_ok()
        msg.state=self.logic.step(self.track_ok(self.track),self.status_ok(self.status) and clock_ok)
        msg.proposal_allowed=clock_ok and msg.state=='TRACK_SHADOW'
        msg.reason='CLOCK_FAULT_RESTART_REQUIRED' if not clock_ok else 'SHADOW_ANALYSIS_ONLY'
        self.publisher.publish(msg)

class Guidance(Base):
    def __init__(self):
        super().__init__('guidance')
        self.subscribe(TargetTrack,'target_track','track')
        self.subscribe(MissionState,'mission_state','mission')
        self.subscribe(AircraftStatus,'aircraft_status','status')
        self.publisher=self.create_publisher(GuidanceProposal,'/alatus/guidance_proposal',10)
        self.timer(self.tick)

    def tick(self):
        p=self.config
        msg=self.stamp(GuidanceProposal(),p['optical_frame_id'])
        msg.shadow_only=True
        allowed=(self.track_ok(self.track) and self.current(self.mission,p['mission_max_age_s'],'mission')
                 and self.mission.proposal_allowed and self.mission.state=='TRACK_SHADOW' and self.status_ok(self.status))
        x,y=(self.track.center_x_norm,self.track.center_y_norm) if self.track else (p['image_center_x'],p['image_center_y'])
        msg.valid,msg.image_error_x,msg.image_error_y,msg.correction_norm=proposal(x,y,allowed,
            p['image_center_x'],p['image_center_y'],p['diagnostic_gain'],p['correction_limit_norm'])
        if self.track: msg.observation_stamp=self.track.header.stamp
        msg.reason='IMAGE_DIAGNOSTIC_ONLY' if msg.valid else 'INVALID_OR_STALE_INPUTS'
        self.publisher.publish(msg)

class SafetyGate(Base):
    def __init__(self):
        super().__init__('safety_gate')
        self.subscribe(GuidanceProposal,'guidance_proposal','proposal')
        self.subscribe(MissionState,'mission_state','mission')
        self.subscribe(AircraftStatus,'aircraft_status','status')
        self.publisher=self.create_publisher(SafetyStatus,'/alatus/safety_status',10)
        self.timer(self.tick)

    def tick(self):
        p,c=self.proposal,self.config
        proposal_ok=(self.current(p,c['proposal_max_age_s'],'proposal') and p.valid
                     and p.header.frame_id==c['optical_frame_id']
                     and fresh(self.now(),seconds(p.observation_stamp),c['observation_max_age_s'])
                     and all(math.isfinite(v) and abs(v)<=1.0+1e-6 for v in (p.image_error_x,p.image_error_y)))
        mission_ok=(self.current(self.mission,c['mission_max_age_s'],'mission') and self.mission.proposal_allowed
                    and self.mission.state=='TRACK_SHADOW')
        msg=self.stamp(SafetyStatus())
        msg.inputs_valid,msg.control_allowed=gate(proposal_ok,mission_ok,self.status_ok(self.status),
            p.shadow_only if p else False,p.correction_norm if p else float('nan'),c['correction_limit_norm'])
        msg.reason='SHADOW_ONLY_NO_CONTROL_IMPLEMENTATION' if msg.inputs_valid else 'INVALID_OR_STALE_INPUTS;CONTROL_PROHIBITED'
        self.publisher.publish(msg)

def run(kind,args=None):
    rclpy.init(args=args)
    node=None
    try:
        node=kind()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None: node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

def mock_perception_main(args=None): run(MockPerception,args)
def tracker_main(args=None): run(Tracker,args)
def mock_status_main(args=None): run(MockStatus,args)
def mission_main(args=None): run(Mission,args)
def guidance_main(args=None): run(Guidance,args)
def safety_gate_main(args=None): run(SafetyGate,args)
