import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data'/'raw'/'agmarknet.json'
payload=json.loads(p.read_text(encoding='utf8')); df=pd.DataFrame(payload['records'])
print('rows:',len(df)); print('columns:',list(df.columns)); print('dtypes:\n',df.dtypes); print('missing:\n',df.isna().sum()); print('sample:\n',df.head(3).to_string(index=False))
