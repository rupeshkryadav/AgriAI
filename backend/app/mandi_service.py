import os
import threading
import time

import pandas as pd
import requests
from fastapi import HTTPException

from .database import SessionLocal
from .models import PlaceCoordinate
from .services import cached_market_frame, live_market_frame, save_mandi_records

_geocode_lock=threading.Lock()
_last_geocode=0.0

def haversine_km(lat1,lon1,lat2,lon2):
    from math import asin,cos,radians,sin,sqrt
    dlat=radians(lat2-lat1);dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2+cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(6371*2*asin(sqrt(a)),1)

def _geocode(place):
    global _last_geocode
    normalized=' '.join(place.casefold().split())
    db=SessionLocal()
    try:
        saved=db.get(PlaceCoordinate,normalized)
        if saved: return saved.latitude,saved.longitude
    finally: db.close()
    with _geocode_lock:
        wait=1.1-(time.monotonic()-_last_geocode)
        if wait>0: time.sleep(wait)
        try:
            response=requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q':place,'format':'jsonv2','limit':1,'countrycodes':'in'},
                headers={'User-Agent':os.getenv('NOMINATIM_USER_AGENT','FarmerConnect/2.0')},
                timeout=12,
            )
            response.raise_for_status();results=response.json();_last_geocode=time.monotonic()
        except (requests.RequestException,ValueError) as exc:
            raise HTTPException(502,'OpenStreetMap could not resolve the mandi coordinates.') from exc
    if not results: return None
    try: latitude,longitude=float(results[0]['lat']),float(results[0]['lon'])
    except (KeyError,TypeError,ValueError): return None
    db=SessionLocal()
    try:
        db.merge(PlaceCoordinate(place=normalized,latitude=latitude,longitude=longitude,source='OpenStreetMap Nominatim'));db.commit()
    finally: db.close()
    return latitude,longitude

def district_options():
    frame=cached_market_frame()
    options=frame[['district','state']].dropna().drop_duplicates().to_dict('records')
    return sorted([{'district':str(x['district']),'state':str(x['state'])} for x in options],key=lambda x:(x['state'],x['district']))

def commodity_options():
    frame=cached_market_frame()
    return sorted(frame['commodity'].dropna().astype(str).unique().tolist())

def market_catalog():
    frame=cached_market_frame()
    districts=frame[['district','state']].dropna().drop_duplicates().to_dict('records')
    return {
        'commodities':sorted(frame['commodity'].dropna().astype(str).unique().tolist()),
        'districts':sorted([{'district':str(x['district']),'state':str(x['state'])} for x in districts],key=lambda x:(x['state'],x['district'])),
        'source':frame.attrs.get('source'),
        'sync_timestamp':frame.attrs.get('sync_timestamp'),
    }

def market_rates(lat=None,lon=None,commodity=None,district=None,state=None):
    if (lat is None)!=(lon is None): raise HTTPException(422,'Provide both latitude and longitude.')
    if lat is None and not district:
        raise HTTPException(422,'Allow browser location or choose your district to calculate mandi distances.')
    if lat is None:
        origin=_geocode(f'{district}, {state or ""}, India')
        if origin is None: raise HTTPException(422,'Could not resolve the selected district. Choose a district from the live mandi list.')
        lat,lon=origin
    frame=live_market_frame(100)
    source=frame.attrs.get('source','live');sync_timestamp=frame.attrs.get('sync_timestamp')
    available_commodities=sorted(frame['commodity'].dropna().astype(str).unique().tolist()) if not frame.empty else []
    available_districts=sorted([{'district':str(x['district']),'state':str(x['state'])} for x in frame[['district','state']].dropna().drop_duplicates().to_dict('records')],key=lambda x:(x['state'],x['district'])) if not frame.empty else []
    if commodity: frame=frame[frame['commodity'].astype(str).str.contains(commodity,case=False,na=False)]
    if frame.empty: return {'source':source,'sync_timestamp':sync_timestamp,'unit':'INR/quintal','commodities':available_commodities,'districts':available_districts,'records':[],'location_used':{'lat':lat,'lon':lon}}
    limit=int(os.getenv('MANDI_DISTANCE_RESULT_LIMIT','20'))
    frame=frame.sort_values('arrival_date',ascending=False).head(max(1,min(limit,50)))
    results=[]
    resolved_coordinates={}
    for row in frame.to_dict('records'):
        place=', '.join(str(row.get(k,'')) for k in ('market','district','state') if row.get(k)) + ', India'
        coords=(row.get('lat'),row.get('lon')) if pd.notna(row.get('lat')) and pd.notna(row.get('lon')) else _geocode(place)
        if coords: resolved_coordinates[', '.join(str(row.get(k,'')) for k in ('market','district','state'))]=coords
        item={k:(None if pd.isna(v) else v.item() if hasattr(v,'item') else v) for k,v in row.items()}
        item['distance_km']=haversine_km(float(lat),float(lon),*coords) if coords else None
        item['latitude'],item['longitude']=coords if coords else (None,None)
        item['trend_pct']=None
        results.append(item)
    if resolved_coordinates:
        save_mandi_records(frame, resolved_coordinates, touch_updated_at=False)
    results.sort(key=lambda r:(r['distance_km'] is None,r['distance_km'] if r['distance_km'] is not None else float('inf')))
    return {'source':source,'sync_timestamp':sync_timestamp,'unit':'INR/quintal','commodities':available_commodities,'districts':available_districts,'distance_source':'OpenStreetMap Nominatim','location_used':{'lat':lat,'lon':lon},'records':results}
