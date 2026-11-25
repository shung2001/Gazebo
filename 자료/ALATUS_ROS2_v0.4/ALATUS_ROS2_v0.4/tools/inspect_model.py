"""Inspect actual supplied file only. Does not download or invent a best.pt."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('model');p.add_argument('--imgsz',type=int,default=640);a=p.parse_args()
x=Path(a.model)
if not x.is_file():raise SystemExit('Model file missing')
print(json.dumps({'path':str(x.resolve()),'suffix':x.suffix,'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'bytes':x.stat().st_size}))
if x.suffix=='.pt':
 from ultralytics import YOLO
 import numpy as np
 m=YOLO(str(x));print('names=',m.names,'task=',m.task);m.info()
 r=m.predict(np.zeros((a.imgsz,a.imgsz,3),dtype=np.uint8),imgsz=a.imgsz,verbose=False)[0]
 print('Synthetic zero-image smoke only; NOT model accuracy.');print('orig_shape=',r.orig_shape,'boxes_shape=',None if r.boxes is None else r.boxes.data.shape,'speed_ms=',r.speed)
else:print('No parser for this runtime. HEF must be inspected with matching Hailo tools; NOT TESTED.')
