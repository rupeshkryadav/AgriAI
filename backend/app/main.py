import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import User, Prediction, Post, Comment, Notification
from .schemas import Register, Login, Profile, PriceRequest, PostInput, CommentInput
from .core import hash_password, verify_password, token_for, decode_token
from .services import market_frame, live_market_frame, predict_price, disease_predict
@asynccontextmanager
async def lifespan(app): Base.metadata.create_all(engine); yield
app=FastAPI(title='AgriAI Farmer Support API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173').split(',')],allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
bearer=HTTPBearer()
def current(creds:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    uid=decode_token(creds.credentials); u=db.get(User,uid) if uid else None
    if not u: raise HTTPException(401,'Invalid or expired token.')
    return u
def user_out(u): return {'id':u.id,'email':u.email,'name':u.name,'state':u.state,'district':u.district,'crops':u.crops}
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/api/system/status')
def system_status():
    root=Path(__file__).resolve().parents[1]
    return {'services':{
        'Live market feed':{'ready':bool(os.getenv('DATA_GOV_API_KEY')),'detail':'India OGD / AGMARKNET API key configured.' if os.getenv('DATA_GOV_API_KEY') else 'DATA_GOV_API_KEY is not configured.'},
        'Historical market data':{'ready':(root/'data'/'processed'/'market_prices.csv').exists(),'detail':'Preprocessed market dataset is available.' if (root/'data'/'processed'/'market_prices.csv').exists() else 'Download and preprocess official market data first.'},
        'Price forecast model':{'ready':(root/'ml'/'artifacts'/'price_model.joblib').exists(),'detail':'Persisted price model is available.' if (root/'ml'/'artifacts'/'price_model.joblib').exists() else 'Train the price model after preprocessing data.'},
        'Crop disease model':{'ready':(root/'ml'/'artifacts'/'disease_model.joblib').exists(),'detail':'Persisted disease model is available.' if (root/'ml'/'artifacts'/'disease_model.joblib').exists() else 'Download approved data and train the disease model.'},
        'Database':{'ready':True,'detail':'Application database is configured; tables initialise on startup.'}
    }}
@app.post('/api/auth/register',status_code=201)
def register(x:Register,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==x.email)): raise HTTPException(409,'Email is already registered.')
    u=User(email=x.email,password_hash=hash_password(x.password),name=x.name,state=x.state,district=x.district,crops=x.crops); db.add(u);db.commit();db.refresh(u)
    return {'access_token':token_for(u.id),'token_type':'bearer','user':user_out(u)}
@app.post('/api/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==x.email))
    if not u or not verify_password(x.password,u.password_hash): raise HTTPException(401,'Incorrect email or password.')
    return {'access_token':token_for(u.id),'token_type':'bearer','user':user_out(u)}
@app.get('/api/users/me')
def me(u:User=Depends(current)): return user_out(u)
@app.put('/api/users/me')
def update_profile(x:Profile,u:User=Depends(current),db:Session=Depends(get_db)):
    for k,v in x.model_dump().items(): setattr(u,k,v)
    db.commit(); return user_out(u)
@app.get('/api/market/prices')
def prices(commodity:str|None=None,state:str|None=None,district:str|None=None,market:str|None=None,limit:int=100,live:bool=True):
    df=live_market_frame(limit) if live else market_frame()
    for col,val in [('commodity',commodity),('state',state),('district',district),('market',market)]:
        if val: df=df[df[col].astype(str).str.contains(val,case=False,na=False)]
    source='Live AGMARKNET/India OGD data' if live else 'Historical imported AGMARKNET/OGD data'
    return {'source':source,'records':df.sort_values('arrival_date',ascending=False).head(min(limit,500)).to_dict('records')}
@app.get('/api/market/options')
def options():
    df=market_frame(); return {x:sorted(df[x].dropna().astype(str).unique().tolist())[:1000] for x in ['commodity','state','district','market','variety']}
@app.post('/api/predictions')
def price_prediction(x:PriceRequest,u:User=Depends(current),db:Session=Depends(get_db)):
    result=predict_price(x); p=Prediction(user_id=u.id,commodity=x.commodity,state=x.state,district=x.district,market=x.market,variety=x.variety,prediction_date=x.prediction_date,predicted_price=result['predicted_price'],reference_price=result['reference_price'],lower=result['range'][0],upper=result['range'][1]); db.add(p);db.add(Notification(user_id=u.id,message=f'Price prediction completed for {x.commodity}.'));db.commit(); return result
@app.get('/api/predictions/recent')
def recent(u:User=Depends(current),db:Session=Depends(get_db)):
    return [{'id':p.id,'commodity':p.commodity,'predicted_price':p.predicted_price,'prediction_date':p.prediction_date,'created_at':p.created_at} for p in db.scalars(select(Prediction).where(Prediction.user_id==u.id).order_by(Prediction.created_at.desc()).limit(10))]
@app.post('/api/disease/predict')
async def disease(image:UploadFile=File(...),u:User=Depends(current)):
    if image.content_type not in {'image/jpeg','image/png','image/webp'}: raise HTTPException(415,'Only JPEG, PNG, and WEBP are allowed.')
    return disease_predict(await image.read())
def post_out(p): return {'id':p.id,'title':p.title,'body':p.body,'category':p.category,'created_at':p.created_at,'author':{'id':p.author.id,'name':p.author.name,'state':p.author.state},'comments':[{'id':c.id,'body':c.body,'created_at':c.created_at,'author':{'id':c.author.id,'name':c.author.name}} for c in p.comments]}
@app.get('/api/posts')
def posts(db:Session=Depends(get_db)): return [post_out(p) for p in db.scalars(select(Post).order_by(Post.created_at.desc())).unique()]
@app.post('/api/posts',status_code=201)
def create_post(x:PostInput,u:User=Depends(current),db:Session=Depends(get_db)):
    p=Post(user_id=u.id,**x.model_dump());db.add(p);db.commit();db.refresh(p);return post_out(p)
@app.put('/api/posts/{post_id}')
def edit_post(post_id:int,x:PostInput,u:User=Depends(current),db:Session=Depends(get_db)):
    p=db.get(Post,post_id)
    if not p: raise HTTPException(404,'Post not found.')
    if p.user_id!=u.id: raise HTTPException(403,'You can edit only your own post.')
    for k,v in x.model_dump().items():setattr(p,k,v)
    db.commit();return post_out(p)
@app.delete('/api/posts/{post_id}',status_code=204)
def delete_post(post_id:int,u:User=Depends(current),db:Session=Depends(get_db)):
    p=db.get(Post,post_id)
    if not p: raise HTTPException(404,'Post not found.')
    if p.user_id!=u.id: raise HTTPException(403,'You can delete only your own post.')
    db.delete(p);db.commit()
@app.post('/api/posts/{post_id}/comments',status_code=201)
def add_comment(post_id:int,x:CommentInput,u:User=Depends(current),db:Session=Depends(get_db)):
    p=db.get(Post,post_id)
    if not p:raise HTTPException(404,'Post not found.')
    c=Comment(post_id=post_id,user_id=u.id,body=x.body);db.add(c)
    if p.user_id!=u.id: db.add(Notification(user_id=p.user_id,message=f'{u.name} replied to your post.'))
    db.commit();return {'id':c.id,'body':c.body}
@app.get('/api/notifications')
def notifications(u:User=Depends(current),db:Session=Depends(get_db)): return [{'id':n.id,'message':n.message,'read':n.read,'created_at':n.created_at} for n in db.scalars(select(Notification).where(Notification.user_id==u.id).order_by(Notification.created_at.desc()).limit(30))]
@app.get('/api/info')
def info(): return [{'title':'Indian Council of Agricultural Research','url':'https://icar.gov.in/'},{'title':'National Horticulture Board','url':'https://nhb.gov.in/'},{'title':'AGMARKNET market information','url':'https://agmarknet.gov.in/'}]
