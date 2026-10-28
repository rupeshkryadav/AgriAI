"""Fetch and persist current, official AGMARKNET observations.

This script never creates synthetic prices. Rows and coordinates are stored only
when returned by data.gov.in and resolved by OpenStreetMap Nominatim.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / '.env')

from app.database import Base, initialize_database  # noqa: E402
from app.services import _normalize_mandi_records, save_mandi_records  # noqa: E402

RESOURCE_URL = os.getenv('LIVE_MARKET_API_URL', 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070')
COMMODITIES = ('Wheat', 'Potato', 'Tomato', 'Rice', 'Mustard', 'Onion', 'Cotton')
MAJOR_DISTRICT_TERMS = (
    'greater noida', 'gautam buddha nagar', 'meerut', 'delhi', 'agra',
    'ludhiana', 'amritsar', 'jalandhar', 'patiala', 'karnal', 'kurukshetra',
    'jaipur', 'indore', 'nagpur', 'lucknow', 'kanpur',
)


def fetch_commodity(session: requests.Session, api_key: str, commodity: str) -> list[dict] | None:
    for attempt in range(4):
        try:
            response = session.get(
                RESOURCE_URL,
                params={'api-key': api_key, 'format': 'json', 'limit': 100, 'filters[commodity]': commodity},
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get('records')
            if not isinstance(rows, list):
                raise ValueError('AGMARKNET response has no records array.')
            return rows
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                print(f'{commodity}: failed after retries: {exc}', file=sys.stderr)
                return None
            delay = 2 ** attempt
            print(f'{commodity}: retry {attempt + 1}/3 in {delay}s ({exc})', file=sys.stderr)
            time.sleep(delay)
    return []


def geocode_place(session: requests.Session, place: str) -> tuple[float, float] | None:
    try:
        response = session.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': f'{place}, India', 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'in'},
            headers={'User-Agent': os.getenv('NOMINATIM_USER_AGENT', 'FarmerConnect/2.0 (mandi data sync)')},
            timeout=30.0,
        )
        response.raise_for_status()
        matches = response.json()
        if not matches:
            return None
        return float(matches[0]['lat']), float(matches[0]['lon'])
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f'Coordinate lookup failed for {place}: {exc}', file=sys.stderr)
        return None


def main() -> int:
    api_key = os.getenv('DATA_GOV_API_KEY')
    if not api_key:
        print('DATA_GOV_API_KEY is missing in backend/.env.', file=sys.stderr)
        return 2
    initialize_database(Base)
    session = requests.Session()
    session.trust_env = False
    collected: list[dict] = []
    for commodity in COMMODITIES:
        rows = fetch_commodity(session, api_key, commodity)
        if rows is None:
            print('The official feed remained unreachable; no new rows were written.', file=sys.stderr)
            return 1
        normalized = _normalize_mandi_records(rows)
        if not normalized.empty:
            # Prefer requested major districts when present. Keep all official
            # records otherwise so valid feed results are not silently discarded.
            district_mask = normalized['district'].str.casefold().apply(
                lambda district: any(term in district for term in MAJOR_DISTRICT_TERMS)
            )
            selected = normalized[district_mask] if district_mask.any() else normalized
            collected.extend(selected.to_dict('records'))
        print(f'{commodity}: {len(normalized)} official rows received')

    if not collected:
        print('No official records were received; existing database contents were left untouched.', file=sys.stderr)
        return 1

    frame = pd.DataFrame(collected).drop_duplicates(
        subset=['commodity', 'variety', 'state', 'district', 'market', 'arrival_date'], keep='last'
    )
    coords: dict[str, tuple[float, float]] = {}
    locations = frame[['market', 'district', 'state']].drop_duplicates().to_dict('records')
    for index, row in enumerate(locations):
        place = ', '.join(str(row[field]) for field in ('market', 'district', 'state'))
        point = geocode_place(session, place)
        if point:
            coords[place] = point
        # Nominatim usage policy asks for a maximum of one request per second.
        if index + 1 < len(locations):
            time.sleep(1.05)

    save_mandi_records(frame, coords)
    print(f'Saved {len(frame)} real AGMARKNET observations; geocoded {len(coords)}/{len(locations)} markets.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
