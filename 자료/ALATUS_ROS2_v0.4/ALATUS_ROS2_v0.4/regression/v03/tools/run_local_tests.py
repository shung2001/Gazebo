from pathlib import Path
import sys, unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src/alatus_runtime'))
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
