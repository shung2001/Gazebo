# Exposure/input timestamp, not inference completion time. Optical frame.
std_msgs/Header header
uint64 sequence
string source
uint32 image_width
uint32 image_height
float64 inference_latency_s
PixelDetection[] detections
