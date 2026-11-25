"""Real ROS parameter API checks. Run beside a fresh shadow.launch.py; not run on the authoring PC."""
import subprocess
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import DescribeParameters, SetParametersAtomically
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType

rclpy.init()
node=Node('alatus_parameter_acceptance')
def call(service,kind,request):
    client=node.create_client(kind,service)
    assert client.wait_for_service(timeout_sec=10), service+' unavailable'
    future=client.call_async(request)
    rclpy.spin_until_future_complete(node,future,timeout_sec=10)
    assert future.done() and future.exception() is None, service+' failed'
    result=future.result()
    node.destroy_client(client)
    return result

def set_one(target,name,value):
    req=SetParametersAtomically.Request()
    req.parameters=[Parameter(name=name,value=value)]
    return call('/'+target+'/set_parameters_atomically',SetParametersAtomically,req).result

try:
    request=DescribeParameters.Request();request.names=['confirm_hits','min_confidence','publish_rate_hz']
    response=call('/tracker/describe_parameters',DescribeParameters,request)
    assert len(response.descriptors)==3 and all(d.read_only for d in response.descriptors)
    assert not set_one('tracker','confirm_hits',ParameterValue(type=ParameterType.PARAMETER_INTEGER,integer_value=4)).successful
    assert not set_one('mission','use_sim_time',ParameterValue(type=ParameterType.PARAMETER_BOOL,bool_value=True)).successful
    assert set_one('mock_perception','dropout',ParameterValue(type=ParameterType.PARAMETER_BOOL,bool_value=True)).successful
    assert set_one('mock_perception','dropout',ParameterValue(type=ParameterType.PARAMETER_BOOL,bool_value=False)).successful
    for arguments in [
        ['tracker','-p','confirm_hits:=0'],
        ['tracker','-p','min_confidence:=.nan'],
        ['mock_perception','-p','center_x_norm:=0.1','-p','amplitude_x_norm:=0.2']]:
        result=subprocess.run(['ros2','run','alatus_runtime',arguments[0],'--ros-args',*arguments[1:]],
                              capture_output=True,text=True,timeout=15)
        assert result.returncode!=0, 'Invalid startup parameters were accepted: '+str(arguments)
    print('ROS parameter acceptance passed: read_only, clock lock, dropout update, invalid startup rejection')
finally:
    node.destroy_node();rclpy.shutdown()
