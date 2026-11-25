# Run the same meaningful pure logic suite under colcon/pytest.
from pathlib import Path
import runpy
globals().update({k:v for k,v in runpy.run_path(str(Path(__file__).resolve().parents[3]/'tests/test_core.py')).items() if k=='CoreTests'})
