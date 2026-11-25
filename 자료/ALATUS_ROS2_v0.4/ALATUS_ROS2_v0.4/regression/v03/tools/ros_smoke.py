"""Run in a sourced Humble shell while shadow.launch.py is running. No command publishers."""
import time
import rclpy
from rclpy.node import Node
from alatus_interfaces.msg import SafetyStatus, MissionState, GuidanceProposal
from std_srvs.srv import SetBool

rclpy.init()
node=Node('alatus_smoke')
seen={}
def receive(key,msg):
    seen[key]=msg
    if key=='safety' and msg.control_allowed:
        raise AssertionError('Unexpected control permission')
for key,kind,topic in [('safety',SafetyStatus,'safety_status'),('mission',MissionState,'mission_state'),('proposal',GuidanceProposal,'guidance_proposal')]:
    node.create_subscription(kind,'/alatus/'+topic,lambda m,k=key:receive(k,m),10)
client=node.create_client(SetBool,'/alatus/shadow_mission')
def wait(predicate,seconds=10):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=0.1)
        if predicate(): return
    raise AssertionError('Timed out: check launch, clock and DDS domain')
try:
    wait(lambda: len(seen)==3)
    assert seen['mission'].state=='IDLE', 'Start with a fresh default launch'
    assert not seen['proposal'].valid
    assert client.wait_for_service(timeout_sec=5)
    req=SetBool.Request(); req.data=True
    future=client.call_async(req)
    wait(future.done)
    assert future.result().success
    wait(lambda: seen['mission'].state=='TRACK_SHADOW' and seen['proposal'].valid and seen['safety'].inputs_valid)
    assert seen['proposal'].shadow_only and not seen['safety'].control_allowed
    print('ROS mock smoke passed: IDLE -> TRACK_SHADOW; control prohibited')
finally:
    if client.service_is_ready():
        req=SetBool.Request(); req.data=False
        future=client.call_async(req)
        rclpy.spin_until_future_complete(node,future,timeout_sec=2)
    node.destroy_node(); rclpy.shutdown()
