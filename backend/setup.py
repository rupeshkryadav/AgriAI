"""Convenience setup launcher; use: python setup.py"""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
subprocess.run([sys.executable,str(root/'ml'/'setup_and_train.py')],check=False)
print('Setup complete. Start the API with: python -m uvicorn app.main:app --reload (from backend/)')
