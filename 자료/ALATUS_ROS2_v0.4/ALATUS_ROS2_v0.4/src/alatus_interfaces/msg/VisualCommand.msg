# Advisory only. Sender has an independent SITL permit and watchdog.
std_msgs/Header header
builtin_interfaces/Time observation_stamp
bool valid
bool shadow_only
string mode
float64 bearing_error_rad
float64 elevation_rad
float64 course_rate_rad_s
float64 bank_diagnostic_rad
float64 flight_path_angle_rad
float64[3] position_enu_m
bool saturated
string reason
