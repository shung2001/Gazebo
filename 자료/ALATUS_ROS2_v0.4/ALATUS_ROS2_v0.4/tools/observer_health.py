"""Read-only health probe: process output, not sensor readiness or flight safety."""
import os
import time
import rclpy
from rclpy.node import Node
from alatus_interfaces.msg import MissionState, SafetyStatus

rclpy.init()
node=Node('observer_health_probe')
seen={}
for key,kind,topic in [('mission',MissionState,'mission_state'),('safety',SafetyStatus,'safety_status')]:
    node.create_subscription(kind,'/alatus/'+topic,lambda msg,k=key: seen.update({k:msg}),10)
deadline=time.monotonic()+4
result=1
try:
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=0.1)
        if len(seen)==2:
            now=node.get_clock().now().nanoseconds
            ages=[(now-m.header.stamp.sec*1000000000-m.header.stamp.nanosec)/1e9 for m in seen.values()]
            expected={'/perception_socket','/tracker','/mission','/guidance','/safety_gate'}
            actual={('/'+namespace.strip('/')+'/'+name).replace('//','/') for name,namespace in node.get_node_names_and_namespaces()}
            if all(0<=age<=1 for age in ages) and expected<=actual and not seen['safety'].control_allowed:
                result=0
                break
finally:
    node.destroy_node(); rclpy.shutdown()
raise SystemExit(result)
