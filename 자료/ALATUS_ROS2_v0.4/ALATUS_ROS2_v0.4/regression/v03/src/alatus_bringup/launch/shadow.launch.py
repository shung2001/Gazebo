from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare('alatus_bringup'), 'config', 'shadow.yaml'])
    names = ['mock_perception', 'tracker', 'mock_status', 'mission', 'guidance', 'safety_gate']
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        *[Node(package='alatus_runtime', executable=name, name=name, output='screen',
               parameters=[config, {'use_sim_time': LaunchConfiguration('use_sim_time')}]) for name in names]])
