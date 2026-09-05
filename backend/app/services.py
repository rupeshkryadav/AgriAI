import os, io, json
from pathlib import Path
import joblib, pandas as pd
from PIL import Image
from fastapi import HTTPException
import requests
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; ART=ROOT/'ml'/'artifacts'
def market_frame():
    p=DATA/'processed'/'market_prices.csv'
    if not p.exists(): raise HTTPException(503,'Market data is not loaded. Run ml/download_data.py and ml/preprocess.py.')
    return pd.read_csv(p, parse_dates=['arrival_date'])
def live_market_frame(limit=100):
    """Fetch current OGD/AGMARKNET records only when a user supplied API key exists."""
    key=os.getenv('DATA_GOV_API_KEY')
    if not key: raise HTTPException(503,'Live market data needs DATA_GOV_API_KEY. Add it to backend/.env and restart the backend.')
    url=os.getenv('LIVE_MARKET_API_URL','https://api.data.gov.in/resource/6141ea17-a69d-4713-b600-0a43c8fd9a6c')
    try:
        # Local development environments may define a stale HTTP(S)_PROXY. Government
        # API calls must not be redirected to an unrelated local proxy.
        session=requests.Session();session.trust_env=False
        timeout=int(os.getenv('LIVE_MARKET_TIMEOUT_SEC','45'))
        response=session.get(url,params={'api-key':key,'format':'json','limit':min(limit,1000)},timeout=timeout);response.raise_for_status();records=response.json().get('records',[])
    except requests.RequestException as exc: raise HTTPException(502,f'Live market source unavailable: {exc}')
    if not records: raise HTTPException(502,'Live market source returned no records.')
    df=pd.DataFrame(records).rename(columns=lambda c:c.strip().lower().replace(' ','_'))
    required={'commodity','state','district','market','arrival_date','min_price','max_price','modal_price'}
    if not required.issubset(df.columns): raise HTTPException(502,f'Live source schema changed; received columns: {", ".join(df.columns)}')
    if 'variety' not in df: df['variety']='Unknown'
    for col in ['min_price','max_price','modal_price']:df[col]=pd.to_numeric(df[col],errors='coerce')
    return df.dropna(subset=['commodity','state','modal_price'])
def predict_price(payload):
    path=ART/'price_model.joblib'; meta=ART/'price_metrics.json'
    if not path.exists(): raise HTTPException(503,'Price model is not trained. Run python ml/train_price.py after preprocessing data.')
    model=joblib.load(path); df=market_frame(); date=pd.Timestamp(payload.prediction_date)
    row={'commodity':payload.commodity,'state':payload.state,'district':payload.district or 'Unknown','market':payload.market or 'Unknown','variety':payload.variety or 'Unknown','year':date.year,'month':date.month,'dayofyear':date.dayofyear}
    try: value=float(model.predict(pd.DataFrame([row]))[0])
    except Exception as e: raise HTTPException(422,f'Unsupported prediction inputs: {e}')
    ref=df[(df.commodity.str.lower()==payload.commodity.lower()) & (df.state.str.lower()==payload.state.lower())]
    reference=float(ref.modal_price.iloc[-1]) if len(ref) else None
    metrics=json.loads(meta.read_text()) if meta.exists() else {}; mae=float(metrics.get('mae',value*.15))
    return {'predicted_price':round(value,2),'unit':'₹/quintal','reference_price':reference,'range':[round(value-mae,2),round(value+mae,2)],'metrics':metrics,'disclaimer':'Estimate from historical AGMARKNET records; not a guarantee or a live quote.'}
def disease_predict(raw:bytes):
    if len(raw)>int(os.getenv('MAX_UPLOAD_MB','5'))*1024*1024: raise HTTPException(413,'Image is too large.')
    try: image=Image.open(io.BytesIO(raw)).convert('RGB')
    except Exception: raise HTTPException(422,'Upload a valid JPEG, PNG, or WEBP image.')
    path=ART/'disease_model.joblib'
    if not path.exists(): raise HTTPException(503,'Disease model is not trained. Download PlantVillage and run ml/train_disease.py.')
    import numpy as np
    clf=joblib.load(path); arr=np.asarray(image.resize((64,64)),dtype='float32').reshape(1,-1)/255
    probs=clf.predict_proba(arr)[0]; i=int(probs.argmax()); label=str(clf.classes_[i]).replace('___',' — ').replace('_',' ')
    return {'label':label,'confidence':round(float(probs[i])*100,1),'advice':'This is a screening estimate only. Isolate affected plants where practical, compare with local extension guidance, and consult an agronomist before applying treatment.'}
