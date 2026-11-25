"""Export the 1280px YOLO11s checkpoint and save an optimized HAR."""

import re
from pathlib import Path

from hailo_sdk_client import ClientRunner
from ultralytics import YOLO


here = Path(__file__).resolve().parent
checkpoint = here / "best_11s.pt"
har_path = here / "best_11s_optimized.har"
if not checkpoint.is_file():
    raise FileNotFoundError(checkpoint)

original_load_model_script = ClientRunner.load_model_script


def load_model_script_without_finetune(self, model_script, *args, **kwargs):
    old = r"post_quantization_optimization\(finetune, policy=enabled, dataset_size=\d+\)"
    model_script, count = re.subn(old, "post_quantization_optimization(finetune, policy=disabled)", model_script)
    if count != 1:
        raise RuntimeError("Expected one Ultralytics DFC fine-tuning command")
    model_script, count = re.subn(
        r"model_optimization_flavor\(optimization_level=2\)",
        "model_optimization_flavor(optimization_level=0)",
        model_script,
    )
    if count != 1:
        raise RuntimeError("Expected one Ultralytics DFC optimization command")
    (here / "model_script.alls").write_text(model_script + "\n", encoding="utf-8")
    return original_load_model_script(self, model_script, *args, **kwargs)


ClientRunner.load_model_script = load_model_script_without_finetune


def save_har_instead_of_compiling(self, *args, **kwargs):
    if args or kwargs:
        raise RuntimeError("Unexpected arguments to DFC compile")
    self.save_har(str(har_path))
    if not har_path.is_file() or har_path.stat().st_size == 0:
        raise RuntimeError("Optimized HAR was not saved")
    print(f"Saved optimized HAR: {har_path}", flush=True)
    return bytes(131072)


ClientRunner.compile = save_har_instead_of_compiling
output_dir = Path(YOLO(str(checkpoint)).export(
    format="hailo",
    name="hailo8",
    imgsz=1280,
    data=str(here / "calibration_data.yaml"),
))
placeholder = output_dir / "best_11s.hef"
if placeholder.is_file() and placeholder.stat().st_size == 131072:
    placeholder.unlink()
else:
    raise RuntimeError("Expected the temporary placeholder HEF")
