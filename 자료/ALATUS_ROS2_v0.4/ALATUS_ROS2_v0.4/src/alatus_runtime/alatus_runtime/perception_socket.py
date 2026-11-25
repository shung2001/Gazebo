"""Linux Unix-datagram inference boundary -> typed ROS TargetDetection."""
import os
import socket
import stat
import time
from pathlib import Path
from alatus_interfaces.msg import TargetDetection
from .nodes import Base, run
from .perception_protocol import Receiver

class PerceptionSocket(Base):
    def __init__(self):
        super().__init__('perception_socket')
        if self.get_parameter('use_sim_time').value:
            raise ValueError('Socket ingress requires same-host system-clock capture times, not sim time')
        import fcntl
        self.path=Path(self.config['socket_path'])
        if not self.path.parent.is_dir(): raise ValueError('Create writable socket directory before launch')
        self.lock=open(str(self.path)+'.lock','a')
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if self.path.exists() or self.path.is_symlink():
            st=self.path.lstat()
            if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=os.getuid():
                raise ValueError('Refusing to replace non-socket or foreign-owned path')
            self.path.unlink()  # Exclusive flock held: only remove a stale socket owned by this user.
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
        self.sock.bind(str(self.path))
        os.chmod(self.path,0o660)
        self.inode=self.path.stat().st_ino
        self.sock.setblocking(False)
        self.receiver=Receiver(self.config['optical_frame_id'],self.config['target_class_id'],
                               self.config['min_confidence'],self.config['max_input_age_s'])
        self.publisher=self.create_publisher(TargetDetection,'/alatus/detection',10)
        self.last_log=0.0
        self.timer(self.tick)

    def tick(self):
        for _ in range(self.config['max_datagrams_per_tick']):
            try: raw=self.sock.recv(65537)
            except BlockingIOError: break
            try:
                if not self.clock_ok(): raise ValueError('Clock fault')
                observation=self.receiver.parse(raw,self.get_clock().now().nanoseconds)
                msg=TargetDetection()
                msg.header.frame_id=self.config['optical_frame_id']
                msg.header.stamp.sec=observation.stamp_ns//1000000000
                msg.header.stamp.nanosec=observation.stamp_ns%1000000000
                msg.valid,msg.confidence=observation.valid,observation.confidence
                msg.center_x_norm,msg.center_y_norm=observation.x,observation.y
                msg.target_id=observation.target_id
                self.publisher.publish(msg)
            except ValueError as error:
                # Malformed input does not refresh a valid observation. Consumer freshness expires.
                if time.monotonic()-self.last_log>1:
                    self.get_logger().warning('Rejected inference input: '+str(error))
                    self.last_log=time.monotonic()

    def destroy_node(self):
        if hasattr(self,'sock'): self.sock.close()
        if hasattr(self,'inode') and self.path.exists() and self.path.stat().st_ino==self.inode:
            self.path.unlink()
        if hasattr(self,'lock'): self.lock.close()
        super().destroy_node()

def main(args=None): run(PerceptionSocket,args)
