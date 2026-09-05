import json
from pathlib import Path
import pandas as pd, joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
ROOT=Path(__file__).resolve().parents[1]; df=pd.read_csv(ROOT/'data'/'processed'/'market_prices.csv',parse_dates=['arrival_date']).sort_values('arrival_date')
for n,fn in [('year',lambda d:d.dt.year),('month',lambda d:d.dt.month),('dayofyear',lambda d:d.dt.dayofyear)]:df[n]=fn(df.arrival_date)
features=['commodity','state','district','market','variety','year','month','dayofyear'];cut=max(1,int(len(df)*.8));tr,te=df.iloc[:cut],df.iloc[cut:]
if len(te)<2: raise SystemExit('Need more time-ordered records to evaluate.')
pre=ColumnTransformer([('cats',OneHotEncoder(handle_unknown='ignore'),features[:5])],remainder='passthrough')
baseline=Pipeline([('pre',pre),('model',DummyRegressor(strategy='median'))]);baseline.fit(tr[features],tr.modal_price)
model=Pipeline([('pre',pre),('model',RandomForestRegressor(n_estimators=200,min_samples_leaf=2,n_jobs=-1,random_state=42))]); model.fit(tr[features],tr.modal_price);pred=model.predict(te[features])
metrics={'mae':round(float(mean_absolute_error(te.modal_price,pred)),2),'rmse':round(float(mean_squared_error(te.modal_price,pred)**.5),2),'r2':round(float(r2_score(te.modal_price,pred)),4),'baseline_mae':round(float(mean_absolute_error(te.modal_price,baseline.predict(te[features]))),2),'model':'RandomForestRegressor','test_rows':len(te),'split':'chronological 80/20'}
art=ROOT/'ml'/'artifacts';art.mkdir(exist_ok=True);joblib.dump(model,art/'price_model.joblib');(art/'price_metrics.json').write_text(json.dumps(metrics,indent=2));print(metrics)
