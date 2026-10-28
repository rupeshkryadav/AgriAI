"""Optional PlantVillage transfer-learning setup.

This script trains a MobileNetV3-Small head for five epochs when PlantVillage
images and PyTorch are available. The API retains its Gemini Vision fallback
when dependencies/data/weights are absent; training is never required to boot.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'plantvillage'
WEIGHTS=ROOT/'ml'/'crop_doctor_model.pt'
CLASSES=ROOT/'ml'/'class_indices.json'
WANTED=('tomato','potato','corn','maize','wheat')

def has_images():
    return DATA.exists() and any(p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'} for p in DATA.rglob('*'))

def ensure_dataset():
    if has_images(): return True
    kaggle_json=Path(os.getenv('KAGGLE_CONFIG_DIR',str(Path.home()/'.kaggle')))/'kaggle.json'
    if (os.getenv('KAGGLE_USERNAME') and os.getenv('KAGGLE_KEY')) or kaggle_json.exists():
        try:
            import kaggle
            DATA.mkdir(parents=True,exist_ok=True)
            kaggle.api.authenticate()
            kaggle.api.dataset_download_files('emmarex/plantdisease',path=str(DATA),unzip=True,quiet=False)
        except Exception as e: print(f'Kaggle download unavailable: {e}')
    return has_images()

def train():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Subset
        from torchvision import datasets, models, transforms
    except ImportError:
        print('PyTorch/torchvision not installed. Add backend/ml/requirements-torch.txt to train; Gemini vision remains available.')
        return False
    if not ensure_dataset():
        print('PlantVillage dataset unavailable. Set Kaggle credentials and rerun; Gemini vision remains available.')
        return False
    train_tf=transforms.Compose([transforms.Resize((224,224)),transforms.RandomHorizontalFlip(),transforms.RandomVerticalFlip(),transforms.RandomRotation(20),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    eval_tf=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    all_data=datasets.ImageFolder(str(DATA),transform=train_tf)
    keep=[i for i,(_,label) in enumerate(all_data.samples) if any(k in all_data.classes[label].lower() for k in WANTED)]
    if not keep: print('No requested crop classes found in dataset.'); return False
    all_data.samples=[all_data.samples[i] for i in keep]
    class_names=sorted({all_data.classes[label] for _,label in all_data.samples})
    remap={all_data.classes.index(name):i for i,name in enumerate(class_names)}
    all_data.classes=class_names; all_data.class_to_idx={name:i for i,name in enumerate(class_names)}
    all_data.samples=[(path,remap[label]) for path,label in all_data.samples]; all_data.targets=[y for _,y in all_data.samples]
    # Cap and shuffle each class independently so alphabetical folders do not
    # accidentally leave later crop types out of the training split.
    import random
    groups={i:[] for i in range(len(class_names))}
    for i,(_,label) in enumerate(all_data.samples): groups[label].append(i)
    train_idx=[]
    for indices in groups.values():
        random.shuffle(indices); train_idx.extend(indices[:2000])
    random.shuffle(train_idx)
    train_ds=Subset(all_data,train_idx)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    for p in model.features.parameters(): p.requires_grad=False
    model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(class_names))
    model.to(device); optimizer=torch.optim.AdamW(model.classifier.parameters(),lr=1e-3); loss_fn=nn.CrossEntropyLoss()
    dl=DataLoader(train_ds,batch_size=32,shuffle=True,num_workers=0)
    for epoch in range(5):
        model.train(); total=0
        for images,labels in dl:
            images,labels=images.to(device),labels.to(device);optimizer.zero_grad();loss=loss_fn(model(images),labels);loss.backward();optimizer.step();total+=loss.item()
        print(f'Epoch {epoch+1}/5 loss={total/max(1,len(dl)):.4f}')
    model.eval(); WEIGHTS.parent.mkdir(parents=True,exist_ok=True); torch.save(model.cpu().state_dict(),WEIGHTS)
    CLASSES.write_text(json.dumps({name:i for i,name in enumerate(class_names)},indent=2),encoding='utf-8')
    print(f'Saved {WEIGHTS} with {len(class_names)} classes on {device}.')
    return True

if __name__=='__main__':
    print('FarmerConnect crop-doctor trainer (5 epochs)')
    try: train()
    except KeyboardInterrupt: sys.exit(130)
