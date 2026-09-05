"""Train a bounded, reproducible baseline on PlantVillage colour folders."""
from pathlib import Path
import numpy as np, joblib
from PIL import Image
from sklearn.linear_model import SGDClassifier
ROOT=Path(__file__).resolve().parents[1]; base=ROOT/'data'/'raw'/'PlantVillage-Dataset'/'raw'/'color'; classes=sorted([p for p in base.iterdir() if p.is_dir()]) if base.exists() else []
if not classes: raise SystemExit(f'PlantVillage colour folders not found at {base}. Run download_plantvillage.py and inspect_data.py first.')
X=[];y=[]
for folder in classes:
    for f in list(folder.glob('*'))[:250]:
        try:X.append(np.asarray(Image.open(f).convert('RGB').resize((64,64)),dtype='float32').reshape(-1)/255);y.append(folder.name)
        except Exception:pass
if len(set(y))<2:raise SystemExit('Insufficient valid labelled images.')
model=SGDClassifier(loss='log_loss',max_iter=1000,random_state=42).fit(np.array(X),y);art=ROOT/'ml'/'artifacts';art.mkdir(exist_ok=True);joblib.dump(model,art/'disease_model.joblib');print({'classes':len(model.classes_),'images':len(y),'per_class_cap':250})
