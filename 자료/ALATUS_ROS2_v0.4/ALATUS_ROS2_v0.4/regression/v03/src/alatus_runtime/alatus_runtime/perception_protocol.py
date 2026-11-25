"""Strict inference-result boundary. This module does not run inference."""
import json
import math
from dataclasses import dataclass

def integer(value,low,high):
    return type(value) is int and low<=value<=high

def number(value):
    return type(value) in (int,float) and math.isfinite(value)

@dataclass
class Observation:
    stamp_ns: int
    valid: bool=False
    confidence: float=0.0
    x: float=0.0
    y: float=0.0
    target_id: int=0

class Receiver:
    def __init__(self,frame='camera_optical',target_class='target',minimum=0.7,max_age_s=0.5):
        self.frame,self.target_class,self.minimum,self.max_age_s=frame,target_class,minimum,max_age_s
        self.stream=None
        self.sequence=-1
        self.stamp_ns=-1

    def parse(self,raw,now_ns):
        if len(raw)>65536: raise ValueError('Oversize datagram')
        try: data=json.loads(raw)
        except (ValueError,UnicodeError) as error: raise ValueError('Malformed JSON') from error
        required={'schema_version','stream_id','sequence','capture_stamp_ns','frame_id','image_width','image_height','detections'}
        if not isinstance(data,dict) or set(data)!=required: raise ValueError('Schema keys mismatch')
        if type(data['schema_version']) is not int or data['schema_version']!=1: raise ValueError('Schema version')
        stream=data['stream_id']
        if type(stream) is not str or not 1<=len(stream)<=64: raise ValueError('Stream ID')
        if self.stream is not None and stream!=self.stream: raise ValueError('New stream requires receiver restart')
        seq,stamp=data['sequence'],data['capture_stamp_ns']
        if not integer(seq,0,2**63-1) or seq<=self.sequence: raise ValueError('Duplicate/out-of-order sequence')
        if not integer(stamp,1,2**63-1) or stamp<=self.stamp_ns: raise ValueError('Non-increasing capture time')
        if not 0<stamp/1e9<2147483648: raise ValueError('ROS Time seconds overflow')
        age=(now_ns-stamp)/1e9
        if not 0<=age<=self.max_age_s: raise ValueError('Stale/future observation')
        if data['frame_id']!=self.frame: raise ValueError('Camera frame mismatch')
        width,height=data['image_width'],data['image_height']
        if not integer(width,1,16384) or not integer(height,1,16384): raise ValueError('Image dimensions')
        detections=data['detections']
        if not isinstance(detections,list) or len(detections)>64: raise ValueError('Detection list')
        candidates=[]
        ids=set()
        for detection in detections:
            if not isinstance(detection,dict) or set(detection)!={'class_id','confidence','track_id','bbox_xywh_px'}:
                raise ValueError('Detection schema')
            score,tid,bbox=detection['confidence'],detection['track_id'],detection['bbox_xywh_px']
            if type(detection['class_id']) is not str: raise ValueError('Class ID')
            if not number(score) or not 0<=score<=1: raise ValueError('Confidence')
            if not integer(tid,0,2**32-1) or tid in ids: raise ValueError('Stable unique uint32 track_id required')
            ids.add(tid)
            if not isinstance(bbox,list) or len(bbox)!=4 or not all(number(v) for v in bbox): raise ValueError('BBox')
            x,y,w,h=bbox
            if x<0 or y<0 or w<=0 or h<=0 or x+w>width or y+h>height: raise ValueError('BBox bounds')
            if detection['class_id']==self.target_class and score>=self.minimum:
                candidates.append((float(score),tid,(x+w/2)/width,(y+h/2)/height))
        result=Observation(stamp)
        if candidates:
            # Deterministic selection; ID change is re-confirmed downstream, not silently treated as the same object.
            score,tid,x,y=sorted(candidates,key=lambda c:(-c[0],c[1]))[0]
            result=Observation(stamp,True,score,float(x),float(y),tid)
        # Commit replay watermark only after all validation succeeded.
        self.stream,self.sequence,self.stamp_ns=stream,seq,stamp
        return result
