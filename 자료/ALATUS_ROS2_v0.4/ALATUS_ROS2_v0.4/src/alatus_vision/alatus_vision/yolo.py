"""Ultralytics detection adapter. No raw tensor/Hailo graph assumptions."""
from pathlib import Path
import json
class Yolo:
    def __init__(self,path,class_id,confidence=.7,imgsz=640):
        if not path or not Path(path).is_file():raise ValueError('MODEL_FILE_NOT_PROVIDED')
        if Path(path).suffix.lower()!='.pt':raise ValueError('This adapter accepts a trusted Ultralytics .pt only; HEF uses host bridge')
        from ultralytics import YOLO
        self.model=YOLO(path,task='detect');self.class_id=class_id;self.confidence=confidence;self.imgsz=imgsz
        if self.model.task!='detect':raise ValueError('Expected detection model')
        if class_id not in self.model.names:raise ValueError('Class ID absent from model')
        print(json.dumps({'model':str(Path(path).resolve()),'names':self.model.names,'requested_imgsz':imgsz,'task':self.model.task}))
    def detect(self,bgr):
        # Official API handles BGR numpy input, letterbox, normalization, NMS and original pixel box restoration.
        result=self.model.predict(source=bgr,imgsz=self.imgsz,conf=self.confidence,classes=[self.class_id],verbose=False)[0]
        if result.boxes is None:return []
        return [(int(cls),float(score),tuple(box)) for cls,score,box in zip(result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.xyxy.cpu().tolist())]
