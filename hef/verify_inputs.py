from pathlib import Path

import onnx
from ultralytics.data.utils import check_det_dataset


here = Path(__file__).resolve().parent
model_path = here / "YOLO11m_best.onnx"
model = onnx.load(str(model_path))
onnx.checker.check_model(model)
print("ONNX graph: OK")
for value in model.graph.input:
    print("input:", value.name, [dim.dim_value for dim in value.type.tensor_type.shape.dim])
for value in model.graph.output:
    print("output:", value.name, [dim.dim_value for dim in value.type.tensor_type.shape.dim])

dataset = check_det_dataset(str(here / "calibration_data.yaml"))
print("calibration train:", dataset["train"])
print("calibration val:", dataset["val"])
