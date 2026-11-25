"""Onboard data observer: no mocks, no auto-start mission, no aircraft control."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, EmitEvent
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    config=LaunchConfiguration('config')
    default=PathJoinSubstitution([FindPackageShare('alatus_bringup'),'config','onboard_observer.yaml'])
    actions=[DeclareLaunchArgument('config',default_value=default),
             DeclareLaunchArgument('enable_px4_status',default_value='false',choices=['true','false'])]
    for executable in ['perception_socket','tracker','mission','guidance','safety_gate']:
        node=Node(package='alatus_runtime',executable=executable,name=executable,output='screen',
                  parameters=[config,{'use_sim_time':False}])
        actions.extend([node,RegisterEventHandler(OnProcessExit(target_action=node,
            on_exit=[EmitEvent(event=Shutdown(reason=executable+' exited; restart complete observer'))]))])
    px4=Node(package='alatus_px4_status',executable='px4_status',name='px4_status',output='screen',
             condition=IfCondition(LaunchConfiguration('enable_px4_status')),parameters=[config,{'use_sim_time':False}])
    actions.extend([px4,RegisterEventHandler(OnProcessExit(target_action=px4,
        on_exit=[EmitEvent(event=Shutdown(reason='PX4 observer exited'))]))])
    return LaunchDescription(actions)
