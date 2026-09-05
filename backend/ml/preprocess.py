import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; raw=ROOT/'data'/'raw'/'agmarknet.json'; out=ROOT/'data'/'processed'/'market_prices.csv'; out.parent.mkdir(parents=True,exist_ok=True)
df=pd.DataFrame(json.loads(raw.read_text(encoding='utf8'))['records']); normalized={c:c.strip().lower().replace(' ','_') for c in df.columns};df=df.rename(columns=normalized)
aliases={'state':'state','district':'district','market':'market','commodity':'commodity','variety':'variety','arrival_date':'arrival_date','min_price':'min_price','max_price':'max_price','modal_price':'modal_price'}
missing=[v for v in aliases.values() if v not in df.columns]
if missing: raise SystemExit(f'OGD schema missing required prediction columns {missing}; inspected columns: {list(df.columns)}')
df['arrival_date']=pd.to_datetime(df['arrival_date'],errors='coerce',dayfirst=True)
for c in ['min_price','max_price','modal_price']:df[c]=pd.to_numeric(df[c],errors='coerce')
df=df.dropna(subset=['arrival_date','commodity','state','modal_price']).drop_duplicates()
df=df[(df.modal_price>0)&(df.modal_price<1_000_000)]
for c in ['district','market','variety']:df[c]=df[c].fillna('Unknown').astype(str)
df.to_csv(out,index=False); print(f'Processed {len(df)} rows to {out}; columns={list(df.columns)}')
