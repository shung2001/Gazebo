"""Compile an optimized Hailo HAR in a fresh process to reduce peak RAM."""

from pathlib import Path

from hailo_sdk_client import ClientRunner


here = Path(__file__).resolve().parent
har_path = here / "YOLO11m_best_optimized.har"
output_dir = here / "YOLO11m_best_hailo_model"
hef_path = output_dir / "YOLO11m_best.hef"

if not har_path.is_file():
    raise FileNotFoundError(har_path)
if not (output_dir / "metadata.yaml").is_file():
    raise FileNotFoundError(output_dir / "metadata.yaml")

runner = ClientRunner(hw_arch="hailo8", har=str(har_path))
runner.load_model_script("performance_param(compiler_optimization_level=0)")
hef_bytes = runner.compile()
if not hef_bytes:
    raise RuntimeError("DFC returned an empty HEF")
temporary_path = hef_path.with_suffix(".hef.tmp")
temporary_path.write_bytes(hef_bytes)
temporary_path.replace(hef_path)
print(f"Saved HEF: {hef_path} ({hef_path.stat().st_size} bytes)")
