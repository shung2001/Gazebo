"""Mock, video, ROS image, or v0.3 host Hailo result socket. No fabricated model."""
import json,os,socket,stat,fcntl,time,uuid
from pathlib import Path
import yaml
from .configuration import validate
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from alatus_interfaces.msg import DetectionFrame,PixelDetection,TargetDetection
from alatus_runtime.perception_protocol import Receiver
from .ros_nodes import spin,stamp

class Perception(Node):
    def __init__(self):
        super().__init__('vision_perception')
        self.c=validate(yaml.safe_load(open(self.declare_parameter('config_path','').value)));c=self.c
        self.publisher=self.create_publisher(DetectionFrame,'/alatus/detection_frame',10)
        self.old=self.create_publisher(TargetDetection,'/alatus/detection',10)
        self.sequence=0;self.source=c['source']+':'+str(uuid.uuid4());self.busy=False
        self.declare_parameter('dropout',False)
        self.last_image_stamp=-1.;self.capture=None;self.sock=None;self.path=None;self.lock=None
        if c['source'] in ['video','image']:
            from .yolo import Yolo
            self.detector=Yolo(c['model_path'],c['class_id'],c['confidence'],c['imgsz'])
        if c['source']=='image':
            from cv_bridge import CvBridge
            self.bridge=CvBridge();self.create_subscription(Image,c['image_topic'],self.image,qos_profile_sensor_data)
        elif c['source']=='video':
            import cv2
            if not Path(c['video_path']).is_file():raise ValueError('Video file missing')
            self.capture=cv2.VideoCapture(c['video_path'])
            if not self.capture.isOpened():raise ValueError('Video cannot open')
            fps=self.capture.get(cv2.CAP_PROP_FPS)
            if not 0<fps<1000:raise ValueError('Video FPS invalid')
            self.create_timer(1./fps,self.video)
        elif c['source']=='mock':self.create_timer(0.05,self.mock)
        elif c['source']=='socket':
            if self.get_parameter('use_sim_time').value:raise ValueError('Socket requires host system time')
            self.path=Path(c.get('socket_path','/run/alatus/perception.sock'))
            self.lock=open(str(self.path)+'.lock','a');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if self.path.exists() or self.path.is_symlink():
                st=self.path.lstat()
                if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=os.getuid():raise ValueError('Unsafe socket path')
                self.path.unlink()
            self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);self.sock.bind(str(self.path));os.chmod(self.path,0o660)
            self.inode=self.path.stat().st_ino;self.sock.setblocking(False)
            self.receiver=Receiver(c['frame_id'],str(c.get('hailo_class_name','target')),c['confidence'],c['input_timeout_s'])
            self.create_timer(.02,self.receive)
        else:raise ValueError('Unknown source')
    def now(self):return self.get_clock().now().nanoseconds/1e9
    def publish(self,t,width,height,ds,latency=0.):
        m=DetectionFrame();m.header.stamp=stamp(t);m.header.frame_id=self.c['frame_id']
        m.sequence=self.sequence;self.sequence+=1;m.source=self.source
        m.image_width=width;m.image_height=height;m.inference_latency_s=latency
        for cls,score,box in ds:
            d=PixelDetection();d.class_id=int(cls);d.confidence=float(score);d.bbox_xyxy_px=list(map(float,box));m.detections.append(d)
        self.publisher.publish(m)
        old=TargetDetection();old.header=m.header
        candidates=[d for d in m.detections if d.class_id==self.c['class_id'] and d.confidence>=self.c['confidence']]
        if len(candidates)==1:
            d=candidates[0];x1,y1,x2,y2=d.bbox_xyxy_px
            if 0<=x1<x2<=width and 0<=y1<y2<=height:
                old.valid=True;old.confidence=d.confidence;old.center_x_norm=(x1+x2)/2/width;old.center_y_norm=(y1+y2)/2/height
        self.old.publish(old)  # target_id=0: compatibility observation, KF assigns identity later.
    def mock(self):
        import math
        t=self.now();u=320+80*math.sin(t*.2)
        ds=[] if self.get_parameter('dropout').value else [(self.c['class_id'],.95,(u-15,225,u+15,255))]
        self.publish(t,640,480,ds)
    def infer(self,frame,t):
        before=time.perf_counter();ds=self.detector.detect(frame)
        self.publish(t,frame.shape[1],frame.shape[0],ds,time.perf_counter()-before)
    def image(self,m):
        t=m.header.stamp.sec+m.header.stamp.nanosec/1e9
        # Preserve capture timestamp; reject stale, future, duplicate frames.
        if t<=self.last_image_stamp or not 0<=self.now()-t<=self.c['input_timeout_s']:return
        if m.header.frame_id!=self.c['frame_id']:return
        self.last_image_stamp=t
        try:self.infer(self.bridge.imgmsg_to_cv2(m,desired_encoding='bgr8'),t)
        except Exception as e:self.get_logger().error('Image inference failure: '+str(e))
    def video(self):
        ok,frame=self.capture.read()
        if not ok:
            self.capture.release();self.capture=None
            # Cancel timer; no looping with refreshed old capture times.
            for timer in self.timers:timer.cancel()
            self.get_logger().info('Replay EOF; downstream expires');return
        # File replay uses current ROS time as replay exposure; offline metrics retain frame index externally.
        self.infer(frame,self.now())
    def receive(self):
        for _ in range(16):
            try:raw=self.sock.recv(65537)
            except BlockingIOError:break
            try:
                self.receiver.parse(raw,self.get_clock().now().nanoseconds)
                d=json.loads(raw);ds=[]
                for box in d['detections']:
                    if box['class_id']!=str(self.c.get('hailo_class_name','target')):continue
                    x,y,w,h=box['bbox_xywh_px'];ds.append((self.c['class_id'],box['confidence'],(x,y,x+w,y+h)))
                self.publish(d['capture_stamp_ns']/1e9,d['image_width'],d['image_height'],ds)
            except ValueError as e:self.get_logger().warning('Rejected Hailo input: '+str(e))
    def destroy_node(self):
        if self.capture is not None:self.capture.release()
        if self.sock is not None:self.sock.close()
        if self.path is not None and self.path.exists() and self.path.stat().st_ino==getattr(self,'inode',None):self.path.unlink()
        if self.lock is not None:self.lock.close()
        super().destroy_node()

def main(args=None):spin(Perception,args)
