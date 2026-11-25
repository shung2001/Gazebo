#!/usr/bin/env python3
import json
import time
from pathlib import Path
from picamera2 import Picamera2
from libcamera import controls

out = Path.home() / "alatus/camera3/tests"
out.mkdir(parents=True, exist_ok=True)
image_path = out / "picamera2_once.jpg"
meta_path = out / "picamera2_once_metadata.json"

cam = Picamera2()
try:
    config = cam.create_still_configuration(main={"size": (1280, 720)})
    cam.configure(config)
    cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
    cam.start()
    time.sleep(2.0)  # 시험용 예열 시간, 운영 지연 성능과 무관
    request = cam.capture_request()
    try:
        metadata = request.get_metadata()  # 이 request의 메타데이터
        request.save("main", str(image_path))
    finally:
        request.release()  # 카메라 버퍼 반환 필수
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print("SAVED_IMAGE", image_path)
    print("SAVED_METADATA", meta_path)
    print("SensorTimestamp", metadata.get("SensorTimestamp", "N/A"))
finally:
    cam.stop()
    cam.close()
