from pathlib import Path
import subprocess
raise SystemExit(subprocess.call(["bash",str(Path(__file__).with_name("test_v04.sh"))]))
