"""Fast, SQLite-backed mandi search. Market requests never parse GIS boundaries."""

from __future__ import annotations

import math

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select

from .database import SessionLocal
from .models import MandiRecord
from .services import cached_market_frame


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates, rounded for display."""
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(6371.0 * 2 * math.asin(math.sqrt(value)), 1)


def _records(state: str | None = None) -> pd.DataFrame:
    frame = cached_market_frame()
    if state and not frame.empty:
        frame = frame[frame['state'].astype(str).str.casefold() == state.strip().casefold()].copy()
        frame.attrs['source'] = 'cached_real'
    return frame


def district_options(state: str | None = None):
    frame = _records(state)
    if frame.empty:
        return []
    return [
        {'district': str(row.district), 'state': str(row.state)}
        for row in frame[['district', 'state']].dropna().drop_duplicates().itertuples(index=False)
    ]


def state_options():
    frame = _records()
    if frame.empty:
        return []
    return sorted(frame['state'].dropna().astype(str).unique().tolist())


def commodity_options():
    db = SessionLocal()
    try:
        return list(db.scalars(select(MandiRecord.commodity).distinct().order_by(MandiRecord.commodity.asc())))
    finally:
        db.close()


def market_catalog():
    frame = _records()
    return {
        'commodities': sorted(frame['commodity'].dropna().astype(str).unique().tolist()) if not frame.empty else [],
        'states': sorted(frame['state'].dropna().astype(str).unique().tolist()) if not frame.empty else [],
        'source': frame.attrs.get('source'),
        'sync_timestamp': frame.attrs.get('sync_timestamp'),
    }


def market_rates(lat=None, lon=None, commodity=None, district=None, state=None):
    if (lat is None) != (lon is None):
        raise HTTPException(422, 'Provide both latitude and longitude.')

    # The browser coordinates are used directly for distance calculations. No
    # reverse-geocoding, polygon parsing, or network calls occur on this route.
    frame = _records(state if lat is None else None)
    if frame.empty:
        return {
            'source': 'sqlite', 'sync_timestamp': None, 'unit': 'INR/quintal',
            'commodities': [], 'districts': [], 'detected_location': None,
            'records': [], 'message': 'No verified mandi records are stored yet.',
        }

    all_commodities = sorted(frame['commodity'].dropna().astype(str).unique().tolist())
    available_districts = district_options(state if lat is None else None)
    if lat is None and district:
        frame = frame[frame['district'].astype(str).str.casefold() == district.strip().casefold()].copy()
    if commodity:
        frame = frame[frame['commodity'].astype(str).str.casefold() == commodity.strip().casefold()].copy()

    frame['_arrival_sort'] = pd.to_datetime(frame['arrival_date'], errors='coerce', dayfirst=True)
    frame = frame.sort_values('_arrival_sort', ascending=False).drop_duplicates(
        subset=['commodity', 'variety', 'state', 'district', 'market'], keep='first'
    ).drop(columns=['_arrival_sort'])

    results = []
    for row in frame.to_dict('records'):
        latitude, longitude = row.get('lat'), row.get('lon')
        has_coordinates = pd.notna(latitude) and pd.notna(longitude)
        distance = haversine_km(float(lat), float(lon), float(latitude), float(longitude)) if lat is not None and has_coordinates else None
        item = {
            key: (None if pd.isna(value) else value.item() if hasattr(value, 'item') else value)
            for key, value in row.items()
        }
        item['distance_km'] = distance
        item['latitude'] = float(latitude) if has_coordinates else None
        item['longitude'] = float(longitude) if has_coordinates else None
        item['trend_pct'] = None
        results.append(item)

    if lat is not None:
        results.sort(key=lambda row: (row['distance_km'] is None, row['distance_km'] if row['distance_km'] is not None else float('inf')))
    else:
        results.sort(key=lambda row: row.get('arrival_date') or '', reverse=True)

    return {
        'source': frame.attrs.get('source') or 'sqlite',
        'sync_timestamp': frame.attrs.get('sync_timestamp'),
        'unit': 'INR/quintal',
        'commodities': all_commodities,
        'districts': available_districts,
        'detected_location': None,
        'location_used': {'lat': lat, 'lon': lon, 'state': state, 'district': district},
        'distance_source': 'precomputed district coordinates with same-state fallback for unmatched district names',
        'records': results[:150],
    }
