from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('firmware_tag', default_value=''),
        DeclareLaunchArgument('px4_msgs_ref', default_value=''),
        DeclareLaunchArgument('status_topic', default_value='/fmu/out/vehicle_status_v1'),
        DeclareLaunchArgument('contract_reviewed', default_value='false'),
        DeclareLaunchArgument('contract_profile_path', default_value=''),
        DeclareLaunchArgument('firmware_commit_sha', default_value=''),
        DeclareLaunchArgument('px4_msgs_commit_sha', default_value=''),
        DeclareLaunchArgument('expected_message_version', default_value='1'),
        Node(package='alatus_px4_status', executable='px4_status', output='screen', parameters=[{
            'firmware_tag': LaunchConfiguration('firmware_tag'),
            'px4_msgs_ref': LaunchConfiguration('px4_msgs_ref'),
            'status_topic': LaunchConfiguration('status_topic'),
            'contract_profile_path': LaunchConfiguration('contract_profile_path'),
            'firmware_commit_sha': LaunchConfiguration('firmware_commit_sha'),
            'px4_msgs_commit_sha': LaunchConfiguration('px4_msgs_commit_sha'),
            'expected_message_version': ParameterValue(LaunchConfiguration('expected_message_version'), value_type=int),
            'contract_reviewed': ParameterValue(LaunchConfiguration('contract_reviewed'), value_type=bool)}])])
