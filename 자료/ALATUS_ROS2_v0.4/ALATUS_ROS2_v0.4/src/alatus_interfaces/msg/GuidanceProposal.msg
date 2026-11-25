# Dimensionless image-space diagnostic. NOT heading, attitude or PX4 setpoint.
std_msgs/Header header
builtin_interfaces/Time observation_stamp
bool valid
bool shadow_only
float32 image_error_x
float32 image_error_y
float32 correction_norm
string reason
