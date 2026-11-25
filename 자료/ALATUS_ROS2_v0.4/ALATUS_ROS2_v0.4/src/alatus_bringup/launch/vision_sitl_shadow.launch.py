from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration,PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    cfg=LaunchConfiguration('config_path')
    default=PathJoinSubstitution([FindPackageShare('alatus_bringup'),'config','v04','vision_sitl_shadow.yaml'])
    actions=[DeclareLaunchArgument('config_path',default_value=default),DeclareLaunchArgument('perception_prefix',default_value='')]
    for executable in ['perception','pipeline']:
        node=Node(package='alatus_vision',executable=executable,prefix=LaunchConfiguration('perception_prefix') if executable=='perception' else '',parameters=[{'config_path':cfg,'use_sim_time':True}],output='screen')
        actions.extend([node,RegisterEventHandler(OnProcessExit(target_action=node,on_exit=[EmitEvent(event=Shutdown(reason=executable+' exited'))]))])
    actions.append(Node(package='alatus_mavros',executable='state_adapter',parameters=[{'use_sim_time':True}],output='screen'))
    return LaunchDescription(actions)
