"""MAVROS ENU/FLU snapshot with conservative per-field validity.
MAV_STATE is NOT PX4 failsafe_flags; manual_input is NOT pilot override.
"""
import time,math
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data as sensor
from geometry_msgs.msg import PoseStamped,TwistStamped
from sensor_msgs.msg import Imu,NavSatFix,BatteryState
from mavros_msgs.msg import State,VfrHud
from alatus_interfaces.msg import AircraftState,AircraftStatus

class StateAdapter(Node):
    def __init__(self):
        super().__init__('mavros_state_adapter')
        self.ns=self.declare_parameter('mavros_namespace','/mavros').value.rstrip('/')
        self.timeout=self.declare_parameter('timeout_s',0.5).value
        self.state_timeout=self.declare_parameter('heartbeat_timeout_s',2.5).value
        self.cache={}
        self.pub=self.create_publisher(AircraftState,'/alatus/aircraft_state',10)
        self.old=self.create_publisher(AircraftStatus,'/alatus/aircraft_status',10)
        for key,kind,topic in [('state',State,'state'),('pose',PoseStamped,'local_position/pose'),
            ('velocity',TwistStamped,'local_position/velocity_local'),('imu',Imu,'imu/data'),
            ('vfr',VfrHud,'vfr_hud'),('gps',NavSatFix,'global_position/raw/fix'),('battery',BatteryState,'battery')]:
            self.create_subscription(kind,self.ns+'/'+topic,lambda m,k=key:self.cache.__setitem__(k,(m,time.monotonic())),sensor)
        self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def get(self,k):
        pair=self.cache.get(k)
        if not pair:return None
        m,receipt=pair;age=self.get_clock().now().nanoseconds/1e9-(m.header.stamp.sec+m.header.stamp.nanosec/1e9)
        timeout=self.state_timeout if k=='state' else self.timeout
        return m if time.monotonic()-receipt<=timeout and 0<=age<=timeout else None
    def tick(self):
        out=AircraftState();out.header.stamp=self.get_clock().now().to_msg();out.header.frame_id='map';out.source='MAVROS'
        now=self.get_clock().now().nanoseconds/1e9
        out.field_age_s=[float(now-(self.cache[k][0].header.stamp.sec+self.cache[k][0].header.stamp.nanosec/1e9)) if k in self.cache else -1.0 for k in ['state','pose','velocity','imu','vfr','gps','battery']]
        s=self.get('state');p=self.get('pose');v=self.get('velocity');i=self.get('imu');a=self.get('vfr');g=self.get('gps');b=self.get('battery')
        if s:
            out.connected=s.connected;out.armed=s.armed;out.mode=s.mode;out.system_status=s.system_status
            # Critical/emergency is affirmative fault evidence; absence is not complete failsafe coverage.
            out.failsafe=s.system_status in [5,6,8];out.failsafe_known=False
        if p:
            out.position_enu_m=[p.pose.position.x,p.pose.position.y,p.pose.position.z]
            out.position_valid=p.header.frame_id=='map' and all(math.isfinite(x) for x in out.position_enu_m)
            out.altitude_local_enu_m=p.pose.position.z
            q=p.pose.orientation;out.attitude_xyzw=[q.x,q.y,q.z,q.w]
            out.attitude_valid=all(math.isfinite(x) for x in out.attitude_xyzw) and abs(sum(x*x for x in out.attitude_xyzw)-1)<.02
        if v:
            out.velocity_enu_m_s=[v.twist.linear.x,v.twist.linear.y,v.twist.linear.z]
            out.velocity_valid=v.header.frame_id=='map' and all(math.isfinite(x) for x in out.velocity_enu_m_s)
        if i:
            out.angular_velocity_flu_rad_s=[i.angular_velocity.x,i.angular_velocity.y,i.angular_velocity.z]
            out.angular_velocity_valid=all(math.isfinite(x) for x in out.angular_velocity_flu_rad_s) and i.angular_velocity_covariance[0]>=0
        if a:out.airspeed_m_s=a.airspeed;out.airspeed_valid=math.isfinite(a.airspeed) and a.airspeed>0
        if g:out.gps_status=g.status.status;out.gps_valid=g.status.status>=0 and math.isfinite(g.latitude) and math.isfinite(g.longitude)
        if b:out.battery_fraction=b.percentage;out.battery_valid=math.isfinite(b.percentage) and 0<=b.percentage<=1
        # All critical field flags become false on link loss, not fresh just because this timer ticks.
        if not out.connected:out.position_valid=out.attitude_valid=out.velocity_valid=out.airspeed_valid=False
        self.pub.publish(out)
        old=AircraftStatus();old.header=out.header;old.status_received=out.connected;old.armed=out.armed
        old.failsafe=out.failsafe;old.source='MAVROS';old.flight_ready_known=False;old.manual_override_known=False
        self.old.publish(old)

def main(args=None):
    rclpy.init(args=args);n=StateAdapter()
    try:rclpy.spin(n)
    except KeyboardInterrupt:pass
    finally:n.destroy_node();rclpy.shutdown()
