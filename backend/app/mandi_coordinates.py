"""Fast state/district coordinate lookup from a precomputed Indian district index."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

COORDINATES_FILE = Path(__file__).resolve().parents[1] / 'data' / 'processed' / 'india_district_coordinates.json'


def _normalise(value: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').casefold()).strip()


def _state_aliases(state: str | None) -> set[str]:
    key = _normalise(state)
    aliases = {
        'delhi': {'delhi', 'nct of delhi', 'national capital territory of delhi'},
        'kerala': {'kerala', 'keralam'},
        'chhattisgarh': {'chhattisgarh', 'chattisgarh'},
        'arunachal pradesh': {'arunachal pradesh', 'arunanchal pradesh'},
        'andaman and nicobar islands': {'andaman and nicobar islands', 'andaman and nicobar island'},
        'dadra and nagar haveli and daman and diu': {
            'dadra and nagar haveli and daman and diu', 'dadra and nagar havelli and daman and diu',
        },
        'odisha': {'odisha', 'orissa'},
        'uttarakhand': {'uttarakhand', 'uttaranchal'},
        'puducherry': {'puducherry', 'pondicherry'},
        'jammu kashmir': {'jammu and kashmir', 'jammu kashmir'},
    }
    for values in aliases.values():
        normalised = {_normalise(value) for value in values}
        if key in normalised:
            return normalised
    return {key}


DISTRICT_ALIASES = {
    'madhya pradesh': {
        'niwadi': 'niwari', 'badwani': 'barwani', 'khandwa': 'east nimar',
        'shehdol': 'shahdol', 'anupur': 'anuppur', 'singroli': 'singrauli',
        'umariya': 'umaria', 'maihar': 'satna', 'mauganj': 'rewa', 'pandhurna': 'chhindwara',
    },
    'punjab': {
        'bhatinda': 'bathinda', 'mohali': 's a s nagar', 'ferozpur': 'firozpur',
        'muktsar': 'sri muktsar sahib', 'ropar rupnagar': 'rupnagar', 'tarntaran': 'tarn taran',
    },
    'rajasthan': {'beawar': 'ajmer'},
    'uttar pradesh': {
        'badaun': 'budaun', 'jalaun orai': 'jalaun', 'kanpur': 'kanpur nagar',
        'bulandshahar': 'bulandshahr', 'raebarelli': 'rae bareli',
        'khiri lakhimpur': 'lakhimpur kheri',
    },
}


@lru_cache(maxsize=1)
def _index():
    if not COORDINATES_FILE.is_file():
        return {}
    payload = json.loads(COORDINATES_FILE.read_text(encoding='utf-8'))
    return {
        (_normalise(row['state']), _normalise(row['district'])): (float(row['lat']), float(row['lon']))
        for row in payload
    }


def district_coordinate(state: str | None, district: str | None) -> tuple[float, float] | None:
    """Return a precomputed district representative coordinate without GIS work."""
    district_key = _normalise(district)
    if not district_key:
        return None
    index = _index()
    state_keys = _state_aliases(state)
    for state_key in state_keys:
        alias = DISTRICT_ALIASES.get(state_key, {}).get(district_key)
        if alias:
            district_key = _normalise(alias)
            break
    for state_key in state_keys:
        point = index.get((state_key, district_key))
        if point:
            return point
    # AGMARKNET occasionally varies district spelling. Only compare within the
    # requested state so a similarly named district elsewhere cannot be chosen.
    candidates = [
        (SequenceMatcher(None, district_key, key_district).ratio(), point)
        for (key_state, key_district), point in index.items()
        if key_state in state_keys
    ]
    candidates.sort(key=lambda item: item[0], reverse=True)
    if candidates and candidates[0][0] >= 0.76 and (len(candidates) == 1 or candidates[0][0] - candidates[1][0] >= 0.08):
        return candidates[0][1]
    # For new districts created after the boundary publication, use the center
    # of that same state's published districts rather than a coordinate from a
    # different state. This is explicitly a coarse state-level estimate.
    state_points = [point for (key_state, _), point in index.items() if key_state in state_keys]
    if not state_points:
        return None
    return (
        sum(point[0] for point in state_points) / len(state_points),
        sum(point[1] for point in state_points) / len(state_points),
    )
