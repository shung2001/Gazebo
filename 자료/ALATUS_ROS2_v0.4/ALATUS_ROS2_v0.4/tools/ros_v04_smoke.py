"""Actual ROS integration acceptance; run while mock_shadow launch is alive."""
import time,math
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from alatus_interfaces.msg import TrackEstimate,VisualCommand,SafetyStatus,MissionState
rclpy.init();n=Node('v04_acceptance');seen={}
for key,kind,topic in [('track',TrackEstimate,'track_estimate'),('cmd',VisualCommand,'visual_command'),('safe',SafetyStatus,'safety_status'),('mission',MissionState,'mission_state')]:
 n.create_subscription(kind,'/alatus/'+topic,lambda m,k=key:seen.__setitem__(k,m),10)
def wait(check,timeout=10):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  rclpy.spin_once(n,timeout_sec=.1)
  if check():return
 raise AssertionError('ROS acceptance timeout: '+str(seen))
wait(lambda:'track' in seen and seen['track'].valid and 'safe' in seen)
client=n.create_client(SetBool,'/alatus/shadow_mission');assert client.wait_for_service(timeout_sec=5)
f=client.call_async(SetBool.Request(data=True));wait(f.done);assert f.result().success
wait(lambda:seen.get('cmd') is not None and seen['cmd'].valid)
assert seen['cmd'].shadow_only and not seen['safe'].control_allowed
assert n.count_publishers('/mavros/setpoint_raw/local')==0
# Request stop resets mission and invalidates proposal.
f=client.call_async(SetBool.Request(data=False));wait(f.done)
wait(lambda:seen['mission'].state=='IDLE' and not seen['cmd'].valid)
print('PASS ROS mock start -> valid guidance -> stop; zero command publishers')
n.destroy_node();rclpy.shutdown()
