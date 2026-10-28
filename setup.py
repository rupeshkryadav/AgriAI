"""Install the API dependencies and attempt the optional crop model training."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'backend'/'requirements.txt')],check=True)
subprocess.run([sys.executable,str(root/'backend'/'ml'/'setup_and_train.py')],check=False)
print('Backend setup finished. Start API: python -m uvicorn app.main:app --app-dir backend --reload')
