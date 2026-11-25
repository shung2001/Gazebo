# Snapshot stamp; per-field stamp+receipt freshness checked by adapter.
std_msgs/Header header
bool connected
bool armed
string mode
bool position_valid
bool attitude_valid
bool velocity_valid
bool angular_velocity_valid
bool airspeed_valid
bool gps_valid
bool battery_valid
bool failsafe_known
bool failsafe
bool manual_override_known
bool manual_override_active
# ENU metres, FLU body quaternion to ENU (xyzw), ENU m/s, FLU rad/s.
float64[3] position_enu_m
float64[4] attitude_xyzw
float64[3] velocity_enu_m_s
float64[3] angular_velocity_flu_rad_s
float64 airspeed_m_s
float64 altitude_local_enu_m
float64 battery_fraction
int32 gps_status
uint8 system_status
# ROS age seconds: State, Pose, Velocity, IMU, VFR, GPS, Battery; -1 means unavailable.
float64[7] field_age_s
string source
