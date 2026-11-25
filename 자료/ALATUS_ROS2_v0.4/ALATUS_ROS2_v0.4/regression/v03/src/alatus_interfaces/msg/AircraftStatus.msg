# Header is ROS receipt time. px4_timestamp_us preserves the received PX4 timestamp.
# DDS may apply time offset; inspect the actual sync/clock configuration before interpreting it.
std_msgs/Header header
uint64 px4_timestamp_us
bool status_received
bool armed
bool failsafe
uint8 nav_state
bool flight_ready_known
bool flight_ready
bool manual_override_known
bool manual_override_active
string source
