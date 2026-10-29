"""Paginate the official AGMARKNET feed and upsert all returned commodities."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / '.env')

from app.database import Base, SessionLocal, initialize_database  # noqa: E402
from app.mandi_coordinates import district_coordinate  # noqa: E402
from app.models import MandiRecord  # noqa: E402
from app.services import _normalize_mandi_records, save_mandi_records  # noqa: E402
from sqlalchemy import select  # noqa: E402

RESOURCE_URL = os.getenv(
    'LIVE_MARKET_API_URL',
    'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070',
)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def fetch_page(session: requests.Session, api_key: str, offset: int, limit: int, state: str | None = None):
    params = {'api-key': api_key, 'format': 'json', 'limit': limit, 'offset': offset}
    if state:
        params['filters[state]'] = state
    for attempt in range(4):
        try:
            response = session.get(RESOURCE_URL, params=params, headers=HEADERS, timeout=30.0)
            response.raise_for_status()
            rows = response.json().get('records')
            if not isinstance(rows, list):
                raise ValueError('AGMARKNET response did not contain a records list.')
            return rows
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            if attempt == 3:
                raise RuntimeError(f'AGMARKNET page at offset {offset} failed: {type(exc).__name__}') from exc
            delay = 2 ** attempt
            print(f'Retrying offset {offset} in {delay}s ({type(exc).__name__}).', file=sys.stderr)
            time.sleep(delay)
    return []


def fetch_batches(session: requests.Session, api_key: str, state: str | None, page_size: int, max_records: int):
    records = []
    for offset in range(0, max_records, page_size):
        batch = fetch_page(session, api_key, offset, min(page_size, max_records - offset), state)
        if not batch:
            break
        records.extend(batch)
        print(f'{state or "India"}: fetched {len(records)} records through offset {offset}.')
        if len(batch) < page_size:
            break
    return records


def coordinate_map(frame):
    resolved = {}
    for row in frame.to_dict('records'):
        point = district_coordinate(row.get('state'), row.get('district'))
        if point:
            key = ', '.join(str(row.get(field) or '') for field in ('market', 'district', 'state'))
            resolved[key] = point
    return resolved


def backfill_existing_coordinates() -> int:
    """Fill coordinates from the precomputed state/district index, without GIS at runtime."""
    db = SessionLocal()
    updated = 0
    try:
        rows = db.scalars(select(MandiRecord).where((MandiRecord.lat.is_(None)) | (MandiRecord.lon.is_(None)))).all()
        for row in rows:
            point = district_coordinate(row.state, row.district)
            if point:
                row.lat, row.lon = point
                updated += 1
        db.commit()
        return updated
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', action='append', help='Optional state filter; may be supplied more than once.')
    parser.add_argument('--page-size', type=int, default=500, help='Records per API page (maximum 500).')
    parser.add_argument('--max-records', type=int, default=1500, help='Maximum records per state/feed.')
    args = parser.parse_args()
    if not 1 <= args.page_size <= 500 or args.max_records < 1:
        parser.error('--page-size must be 1..500 and --max-records must be positive.')
    api_key = os.getenv('DATA_GOV_API_KEY')
    if not api_key:
        print('DATA_GOV_API_KEY is missing in backend/.env.', file=sys.stderr)
        return 2

    initialize_database(Base)
    try:
        with requests.Session() as session:
            states = args.state or [None]
            total = 0
            for state in states:
                rows = fetch_batches(session, api_key, state, args.page_size, args.max_records)
                frame = _normalize_mandi_records(rows)
                if frame.empty:
                    print(f'{state or "India"}: no valid official records returned.')
                    continue
                frame = frame.drop_duplicates(
                    subset=['commodity', 'variety', 'state', 'district', 'market', 'arrival_date'], keep='last'
                )
                coords = coordinate_map(frame)
                save_mandi_records(frame, coords)
                total += len(frame)
                print(f'{state or "India"}: upserted {len(frame)} records across {frame.commodity.nunique()} commodities; mapped {len(coords)} district locations.')
            backfilled = backfill_existing_coordinates()
            print(f'Sync complete: {total} official records upserted; coordinates filled for {backfilled} existing records.')
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
