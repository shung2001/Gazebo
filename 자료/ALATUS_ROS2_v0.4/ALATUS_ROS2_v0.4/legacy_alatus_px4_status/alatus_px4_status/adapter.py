"""Version-gated, read-only VehicleStatus adapter. No PX4 command publishers."""
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from alatus_interfaces.msg import AircraftStatus
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from alatus_runtime.compatibility import load_profile, validate_profile
from alatus_runtime.ros_parameters import configure

class Adapter(Node):
    def __init__(self):
        super().__init__('px4_status')
        p=self.config=configure(self,'px4_status')
        profile=load_profile(p['contract_profile_path'])
        if not p['contract_reviewed'] or profile.get('reviewed') is not True:
            raise ValueError('Compatibility review incomplete')
        from px4_msgs.msg import VehicleStatus
        definition=(Path(get_package_share_directory('px4_msgs'))/'msg/VehicleStatus.msg').read_bytes()
        validate_profile(p,profile,getattr(VehicleStatus,'MESSAGE_VERSION',-1),
                         VehicleStatus.get_fields_and_field_types(),VehicleStatus.ARMING_STATE_ARMED,definition)
        self.get_logger().info('Declared provenance: firmware='+p['firmware_commit_sha']+' px4_msgs='+p['px4_msgs_commit_sha']+
                               '; not automatic firmware/schema attestation')
        self.publisher=self.create_publisher(AircraftStatus,'/alatus/aircraft_status',10)
        self.create_subscription(VehicleStatus,p['status_topic'],self.receive,qos_profile_sensor_data)

    def receive(self,status):
        msg=AircraftStatus()
        msg.header.stamp=self.get_clock().now().to_msg()
        msg.px4_timestamp_us=status.timestamp
        msg.status_received=True
        msg.armed=status.arming_state==status.ARMING_STATE_ARMED
        msg.failsafe=status.failsafe
        msg.nav_state=status.nav_state
        msg.source='PX4_VEHICLE_STATUS_ONLY'
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node=None
    try:
        node=Adapter()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None: node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
