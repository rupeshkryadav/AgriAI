"""Download the public PlantVillage repository; it is large (~2GB)."""
import subprocess
from pathlib import Path
dst=Path(__file__).resolve().parents[1]/'data'/'raw'/'PlantVillage-Dataset'
if dst.exists(): print(dst); raise SystemExit(0)
subprocess.run(['git','clone','--depth','1','https://github.com/spMohanty/PlantVillage-Dataset.git',str(dst)],check=True)
