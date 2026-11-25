"""Vendor-independent hook for an already-working Hailo pipeline.

No Hailo API/model/preprocessing assumptions. Supply original-image boxes and
stable tracker IDs from the selected pipeline, with a mapped exposure timestamp.
"""
import json
import socket
import uuid

class ResultClient:
    def __init__(self,path='/run/alatus/perception.sock'):
        self.path=path
        self.stream_id=str(uuid.uuid4())
        self.sequence=0
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
        self.socket.settimeout(0.02)

    def send(self,capture_stamp_ns,width,height,detections,frame_id='camera_optical'):
        data={'schema_version':1,'stream_id':self.stream_id,'sequence':self.sequence,
              'capture_stamp_ns':capture_stamp_ns,'frame_id':frame_id,
              'image_width':width,'image_height':height,'detections':detections}
        packet=json.dumps(data,allow_nan=False,separators=(',',':')).encode()
        if len(packet)>65536: raise ValueError('Too many detections')
        self.sequence+=1
        try:
            self.socket.sendto(packet,self.path)
            return True
        except (OSError,TimeoutError):
            # Dropping a frame is explicit; do not block the camera/inference pipeline.
            return False

    def close(self): self.socket.close()
