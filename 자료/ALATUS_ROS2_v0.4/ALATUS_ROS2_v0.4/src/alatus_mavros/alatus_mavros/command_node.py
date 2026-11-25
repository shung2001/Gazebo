"""Explicit opt-in SITL transmitter. No arm/mode services; never launched in shadow."""
import json,time,math
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data
from std_srvs.srv import SetBool
from rcl_interfaces.srv import GetParameters
from mavros_msgs.msg import PositionTarget
from alatus_interfaces.msg import AircraftState,VisualCommand,TrackEstimate,MissionState,SafetyStatus
from .authority import validate_permit,local_sitl,eligible

def seconds(s):return s.sec+s.nanosec*1e-9
class Sender(Node):
    def __init__(self):
        super().__init__('sitl_command_sender')
        path=self.declare_parameter('permit_path','').value
        self.permit=json.load(open(path));validate_permit(self.permit)
        self.pid=self.declare_parameter('sitl_pid',0).value
        if not local_sitl(self.pid):raise ValueError('Local PX4 SITL process required')
        self.link_client=self.create_client(GetParameters,'/mavros_router/get_parameters')
        self.link_future=None;self.link_ok=False;self.link_checked=-math.inf
        self.enabled=False;self.revoked=False;self.seen_offboard=False;self.cache={};self.last_clock=None;self.last_progress=time.monotonic()
        self.pub=self.create_publisher(PositionTarget,'/mavros/setpoint_raw/local',qos_profile_sensor_data)
        self.authority=self.create_publisher(SafetyStatus,'/alatus/sitl_authority',10)
        for key,kind,topic in [('state',AircraftState,'aircraft_state'),('cmd',VisualCommand,'visual_command'),('track',TrackEstimate,'track_estimate'),('mission',MissionState,'mission_state')]:
            self.create_subscription(kind,'/alatus/'+topic,lambda m,k=key:self.cache.__setitem__(k,(m,time.monotonic())),10)
        self.create_service(SetBool,'/alatus/sitl_stream_enable',self.enable)
        self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def enable(self,req,res):
        if not req.data:self.enabled=False;self.revoked=True
        elif not self.revoked:self.enabled=True
        res.success=not req.data or self.enabled
        res.message='Restart sender after revoke. Prestream in AUTO.LOITER, then explicitly select OFFBOARD; no auto arming/mode.'
        return res
    def tick(self):
        now=self.get_clock().now().nanoseconds/1e9;wall=time.monotonic();reason='DISABLED';ok=False
        if self.last_clock is not None:
            if now<self.last_clock:self.revoked=True
            if now>self.last_clock:self.last_progress=wall
            elif wall-self.last_progress>.25:self.revoked=True
        self.last_clock=now
        if self.link_future is not None and self.link_future.done():
            try:
                values=self.link_future.result().values
                self.link_ok=len(values)==1 and list(values[0].string_array_value)==[self.permit['fcu_url']]
                self.link_checked=wall
            except Exception:self.link_ok=False
            self.link_future=None
        if self.link_future is None and wall-self.link_checked>.2 and self.link_client.service_is_ready():
            self.link_future=self.link_client.call_async(GetParameters.Request(names=['fcu_urls']))
        boundary_ok=self.link_ok and wall-self.link_checked<1.0 and local_sitl(self.pid) and len(self.cache)==4
        if self.enabled and self.seen_offboard and not boundary_ok:self.revoked=True
        if self.enabled and not self.revoked and boundary_ok:
            s,rs=self.cache['state'];c,rc=self.cache['cmd'];tr,rt=self.cache['track'];m,rm=self.cache['mission']
            if self.seen_offboard and s.mode!='OFFBOARD':self.revoked=True
            if s.mode=='OFFBOARD':self.seen_offboard=True
            sd=dict(stamp=seconds(s.header.stamp),source=s.source,connected=s.connected,armed=s.armed,
                position_valid=s.position_valid,attitude_valid=s.attitude_valid,velocity_valid=s.velocity_valid,airspeed_valid=s.airspeed_valid,
                failsafe=s.failsafe,manual_override_active=s.manual_override_active,mode=s.mode,
                position=list(s.position_enu_m),q=list(s.attitude_xyzw),airspeed=s.airspeed_m_s)
            cd=dict(stamp=seconds(c.header.stamp),observation_stamp=seconds(c.observation_stamp),valid=c.valid,target=list(c.position_enu_m))
            ok,reason=eligible(self.permit,sd,cd,tr.valid,m.state,now,max(wall-rs,wall-rc,wall-rt,wall-rm))
            if tr.source.startswith('mock:') and not self.permit.get('mock_input_reviewed',False):ok=False;reason='MOCK_INPUT_NOT_REVIEWED'
            for topic in ['aircraft_state','visual_command','track_estimate','mission_state']:
                if len(self.get_publishers_info_by_topic('/alatus/'+topic))!=1:ok=False;reason='DUPLICATE_OR_MISSING_PUBLISHER'
            competing=['/mavros/setpoint_position/local','/mavros/setpoint_position/global','/mavros/setpoint_raw/global','/mavros/setpoint_raw/attitude','/mavros/setpoint_attitude/attitude','/mavros/setpoint_velocity/cmd_vel','/mavros/setpoint_velocity/cmd_vel_unstamped','/mavros/setpoint_accel/accel']
            if self.count_publishers('/mavros/setpoint_raw/local')!=1 or any(self.count_publishers(t)>0 for t in competing):
                ok=False;reason='COMPETING_COMMAND_PUBLISHER'
            if self.revoked:ok=False;reason='MODE_EXIT_REVOKED'
            if ok:
                msg=PositionTarget();msg.header.stamp=self.get_clock().now().to_msg();msg.header.frame_id='map'
                msg.coordinate_frame=PositionTarget.FRAME_LOCAL_NED
                # API expects ENU values even though MAVLink enum says NED. MAVROS converts exactly once.
                msg.type_mask=PositionTarget.IGNORE_VX|PositionTarget.IGNORE_VY|PositionTarget.IGNORE_VZ|PositionTarget.IGNORE_AFX|PositionTarget.IGNORE_AFY|PositionTarget.IGNORE_AFZ|PositionTarget.IGNORE_YAW|PositionTarget.IGNORE_YAW_RATE
                msg.position.x,msg.position.y,msg.position.z=c.position_enu_m
                self.pub.publish(msg)
            elif self.seen_offboard:self.revoked=True
        out=SafetyStatus();out.header.stamp=self.get_clock().now().to_msg();out.inputs_valid=ok;out.control_allowed=ok;out.reason=reason
        self.authority.publish(out)

def main(args=None):
    rclpy.init(args=args);n=Sender()
    try:rclpy.spin(n)
    except KeyboardInterrupt:pass
    finally:n.destroy_node();rclpy.shutdown()
