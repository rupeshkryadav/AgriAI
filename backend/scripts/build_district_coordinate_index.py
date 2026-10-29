"""Precompute district representative coordinates from official SOI GeoJSON.

Requires optional `shapely` and `pyproj` packages and the NWIC download zip.
The generated JSON is tiny; runtime only performs a dictionary lookup.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'backend' / 'data' / 'processed' / 'india_district_coordinates.json'


def read_features(source):
    """Stream GeoJSON feature objects so the 168 MB source is not loaded whole."""
    decoder = json.JSONDecoder()
    buffer = ''
    started = False
    ended = False
    while not ended:
        chunk = source.read(1024 * 1024)
        if not chunk:
            break
        buffer += chunk
        if not started:
            marker = buffer.find('"features"')
            if marker < 0:
                buffer = buffer[-32:]
                continue
            opening = buffer.find('[', marker)
            if opening < 0:
                continue
            buffer = buffer[opening + 1:]
            started = True
        cursor = 0
        while True:
            while cursor < len(buffer) and buffer[cursor] in ' \r\n\t,':
                cursor += 1
            if cursor >= len(buffer):
                buffer = ''
                break
            if buffer[cursor] == ']':
                ended = True
                break
            try:
                feature, next_cursor = decoder.raw_decode(buffer, cursor)
            except json.JSONDecodeError:
                buffer = buffer[cursor:]
                cursor = 0
                break
            yield feature
            cursor = next_cursor
        if cursor and not ended:
            buffer = buffer[cursor:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='NWIC district_nwic_geojson.zip or uncompressed GeoJSON')
    args = parser.parse_args()
    transformer = Transformer.from_crs('EPSG:7755', 'EPSG:4326', always_xy=True)
    output = []
    if zipfile.is_zipfile(args.source):
        archive = zipfile.ZipFile(args.source)
        geojson_name = next(name for name in archive.namelist() if name.casefold().endswith('.geojson'))
        source = io.TextIOWrapper(archive.open(geojson_name), encoding='utf-8')
    else:
        source = args.source.open('r', encoding='utf-8')
    with source:
        for feature in read_features(source):
            properties = feature.get('properties') or {}
            state = str(properties.get('state_name') or '').strip()
            district = str(properties.get('district') or '').strip()
            if not state or not district or not feature.get('geometry'):
                continue
            point = shape(feature['geometry']).representative_point()
            longitude, latitude = transformer.transform(point.x, point.y)
            output.append({'state': state, 'district': district, 'lat': round(latitude, 7), 'lon': round(longitude, 7)})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(output)} district coordinates to {OUTPUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
