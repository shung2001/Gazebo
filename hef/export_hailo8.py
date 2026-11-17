"""Optimize the checkpoint and save a HAR before compiling in a fresh process."""

import re
import shutil
from pathlib import Path

from hailo_sdk_client import ClientRunner
from ultralytics import YOLO


here = Path(__file__).resolve().parent
checkpoint_path = here / "YOLO11m_best.pt"
if not checkpoint_path.is_file():
    shutil.copy2(here.parent / "YOLO11m_best.pt", checkpoint_path)
har_path = here / "YOLO11m_best_optimized.har"
original_load_model_script = ClientRunner.load_model_script


def load_model_script_without_finetune(self, model_script, *args, **kwargs):
    old = r"post_quantization_optimization\(finetune, policy=enabled, dataset_size=\d+\)"
    model_script, replacements = re.subn(
        old, "post_quantization_optimization(finetune, policy=disabled)", model_script
    )
    if replacements != 1:
        raise RuntimeError("Expected one Ultralytics DFC fine-tuning command")
    (here / "model_script.alls").write_text(model_script + "\n", encoding="utf-8")
    print("DFC fine-tuning disabled after WSL ran out of memory", flush=True)
    return original_load_model_script(self, model_script, *args, **kwargs)


ClientRunner.load_model_script = load_model_script_without_finetune


def save_har_instead_of_compiling(self, *args, **kwargs):
    if args or kwargs:
        raise RuntimeError("Unexpected arguments to DFC compile")
    self.save_har(str(har_path))
    if not har_path.is_file() or har_path.stat().st_size == 0:
        raise RuntimeError("Optimized HAR was not saved")
    print(f"Saved optimized HAR: {har_path}", flush=True)
    # Ultralytics checks the size of its temporary export before returning.
    return bytes(131072)


ClientRunner.compile = save_har_instead_of_compiling
output_dir = Path(YOLO(str(checkpoint_path)).export(
    format="hailo",
    name="hailo8",
    imgsz=512,
    data=str(here / "calibration_data.yaml"),
))
placeholder = output_dir / "YOLO11m_best.hef"
if placeholder.is_file() and placeholder.stat().st_size == 131072:
    placeholder.unlink()
else:
    raise RuntimeError("Expected the temporary placeholder HEF")
