import json, os
from pathlib import Path
import joblib
import pandas as pd
import requests
from fastapi import HTTPException
from datetime import datetime, timezone
from sqlalchemy import select
from dotenv import load_dotenv
from .database import SessionLocal
from .models import MandiRecord

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
ART=ROOT/'ml'/'artifacts'
load_dotenv(ROOT/'.env')

def market_frame():
    path=DATA/'processed'/'market_prices.csv'
    if not path.exists():
        raise HTTPException(503,'Market history has not been imported and processed yet.')
    return pd.read_csv(path,parse_dates=['arrival_date'])

def live_market_frame(limit=100):
    """Return verified live data when available, otherwise the last persisted real feed."""
    key=os.getenv('DATA_GOV_API_KEY')
    url=os.getenv('LIVE_MARKET_API_URL','https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070')
    last_error=None
    try:
        if not key: raise RuntimeError('DATA_GOV_API_KEY is not configured.')
        session=requests.Session()
        response=session.get(url,params={'api-key':key,'format':'json','limit':min(max(int(limit),1),100)},timeout=30.0)
        response.raise_for_status()
        records=response.json().get('records',[])
        frame=_normalize_mandi_records(records)
        if not frame.empty:
            sync_timestamp=save_mandi_records(frame)
            frame.attrs['source']='live'
            frame.attrs['sync_timestamp']=sync_timestamp
            return frame
        last_error='The live AGMARKNET request returned no records.'
    except (requests.RequestException,ValueError,RuntimeError,TypeError,AttributeError) as exc:
        last_error=str(exc)
    frame,cached_at=read_cached_mandi_records()
    if not frame.empty:
        frame.attrs['source']='cached_real'
        frame.attrs['sync_timestamp']=cached_at
        return frame
    raise HTTPException(503,f'No verified mandi records are cached and the live data.gov.in feed could not be read: {last_error}')

def _normalize_mandi_records(records):
    if not records: return pd.DataFrame(columns=['commodity','variety','state','district','market','arrival_date','min_price','max_price','modal_price'])
    frame=pd.DataFrame(records).rename(columns=lambda c:c.strip().lower().replace(' ','_'))
    required={'commodity','state','district','market','arrival_date','min_price','max_price','modal_price'}
    if not required.issubset(frame.columns): raise ValueError('The data.gov.in response does not contain expected AGMARKNET fields.')
    if 'variety' not in frame: frame['variety']=None
    for col in ('min_price','max_price','modal_price'): frame[col]=pd.to_numeric(frame[col],errors='coerce')
    frame=frame.dropna(subset=['commodity','state','district','market','modal_price'])
    for col in ('commodity','state','district','market','arrival_date'):
        frame[col]=frame[col].fillna('').astype(str).str.strip()
    frame['variety']=frame['variety'].fillna('').astype(str).str.strip()
    return frame

def save_mandi_records(frame, coordinates=None, touch_updated_at=True):
    db=SessionLocal(); now=datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        for row in frame.to_dict('records'):
            coord=(coordinates or {}).get(', '.join((str(row.get('market','')),str(row.get('district','')),str(row.get('state','')))))
            existing=db.scalar(select(MandiRecord).where(MandiRecord.commodity==row['commodity'],MandiRecord.variety==row.get('variety') or '',MandiRecord.state==row['state'],MandiRecord.district==row['district'],MandiRecord.market==row['market'],MandiRecord.arrival_date==row['arrival_date']))
            values=dict(commodity=row['commodity'],variety=row.get('variety') or '',state=row['state'],district=row['district'],market=row['market'],min_price=None if pd.isna(row.get('min_price')) else float(row['min_price']),max_price=None if pd.isna(row.get('max_price')) else float(row['max_price']),modal_price=float(row['modal_price']),arrival_date=row['arrival_date'],lat=coord[0] if coord else (existing.lat if existing else None),lon=coord[1] if coord else (existing.lon if existing else None))
            if touch_updated_at: values['updated_at']=now
            if existing:
                for key,value in values.items(): setattr(existing,key,value)
            else: db.add(MandiRecord(**values))
        db.commit()
        return now.isoformat()
    except Exception:
        db.rollback(); raise
    finally: db.close()

def read_cached_mandi_records():
    db=SessionLocal()
    try:
        rows=db.scalars(select(MandiRecord).order_by(MandiRecord.arrival_date.desc())).all()
        if not rows: return pd.DataFrame(columns=['commodity','variety','state','district','market','min_price','max_price','modal_price','arrival_date','lat','lon']),None
        latest=max(row.updated_at for row in rows)
        return pd.DataFrame([{'commodity':r.commodity,'variety':r.variety,'state':r.state,'district':r.district,'market':r.market,'min_price':r.min_price,'max_price':r.max_price,'modal_price':r.modal_price,'arrival_date':r.arrival_date,'lat':r.lat,'lon':r.lon} for r in rows]),latest.replace(tzinfo=timezone.utc).isoformat()
    finally: db.close()

def cached_market_frame():
    frame,sync_timestamp=read_cached_mandi_records()
    frame.attrs['source']='cached_real' if not frame.empty else None
    frame.attrs['sync_timestamp']=sync_timestamp
    return frame

def predict_price(payload):
    path=ART/'price_model.joblib'; meta=ART/'price_metrics.json'
    if not path.exists(): raise HTTPException(503,'Price model is not trained yet.')
    model=joblib.load(path); frame=market_frame(); date=pd.Timestamp(payload.prediction_date)
    row={'commodity':payload.commodity,'state':payload.state,'district':payload.district or 'Unknown','market':payload.market or 'Unknown','variety':payload.variety or 'Unknown','year':date.year,'month':date.month,'dayofyear':date.dayofyear}
    try: value=float(model.predict(pd.DataFrame([row]))[0])
    except Exception as exc: raise HTTPException(422,'The model cannot process these prediction inputs.') from exc
    ref=frame[(frame.commodity.str.lower()==payload.commodity.lower()) & (frame.state.str.lower()==payload.state.lower())]
    reference=float(ref.modal_price.iloc[-1]) if len(ref) else None
    metrics=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}; mae=float(metrics.get('mae',value*.15))
    return {'predicted_price':round(value,2),'unit':'₹/quintal','reference_price':reference,'range':[round(value-mae,2),round(value+mae,2)],'metrics':metrics,'disclaimer':'Forecast based on imported historical records; not a live quote or guarantee.'}
