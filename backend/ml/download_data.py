"""Download AGMARKNET OGD records. Requires DATA_GOV_API_KEY in environment."""
import os, json, requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'data'/'raw'/'agmarknet.json'; out.parent.mkdir(parents=True,exist_ok=True)
key=os.environ.get('DATA_GOV_API_KEY')
if not key: raise SystemExit('Set DATA_GOV_API_KEY (obtain one at https://data.gov.in/apis). No fabricated data is generated.')
url='https://api.data.gov.in/resource/6141ea17-a69d-4713-b600-0a43c8fd9a6c'
r=requests.get(url,params={'api-key':key,'format':'json','limit':10000},timeout=60);r.raise_for_status(); payload=r.json()
if not isinstance(payload.get('records'),list) or not payload['records']: raise SystemExit(f'Unexpected/empty OGD response: {payload.keys()}')
out.write_text(json.dumps(payload,indent=2),encoding='utf8'); print(f'Downloaded {len(payload["records"])} records to {out}')
