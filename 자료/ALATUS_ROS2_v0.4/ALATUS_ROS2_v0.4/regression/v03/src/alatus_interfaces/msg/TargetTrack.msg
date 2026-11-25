# Header retains source observation time, never refresh stale observations.
std_msgs/Header header
bool valid
float32 confidence
float32 center_x_norm
float32 center_y_norm
uint32 track_id
uint32 consecutive_hits
