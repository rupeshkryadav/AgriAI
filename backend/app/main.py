import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from .database import Base, engine, get_db, initialize_database
from .models import User, Prediction, Post, PostLike, Comment, Notification
from .schemas import Register, Login, Profile, PriceRequest, PostInput, CommentInput
from .core import hash_password, verify_password, token_for, decode_token
from .services import market_frame, live_market_frame, predict_price
from .ai_service import diagnose_leaf
@asynccontextmanager
async def lifespan(app): initialize_database(Base); yield
app=FastAPI(title='FarmerConnect API',version='2.0.0',lifespan=lifespan)
from .routers.ai_doctor import router as ai_doctor_router
from .routers.market import router as mandi_router
from .routers.community import router as community_router
app.include_router(ai_doctor_router); app.include_router(mandi_router); app.include_router(community_router)
UPLOAD_DIR=Path(__file__).resolve().parents[1]/'uploads'; UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
app.mount('/uploads',StaticFiles(directory=UPLOAD_DIR),name='uploads')
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
        'Crop disease model':{'ready':(root/'ml'/'crop_doctor_model.pt').exists() or (root/'ml'/'artifacts'/'disease_model.joblib').exists(),'detail':'Persisted crop doctor model is available.' if (root/'ml'/'crop_doctor_model.pt').exists() or (root/'ml'/'artifacts'/'disease_model.joblib').exists() else 'Train locally or configure GEMINI_API_KEY for vision fallback.'},
        'AI Doctor':{'ready':bool(os.getenv('GEMINI_API_KEY')),'detail':'Gemini advice and multilingual chat are configured.' if os.getenv('GEMINI_API_KEY') else 'Configure GEMINI_API_KEY for AI-generated advice.'},
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
async def disease(image:UploadFile=File(...),language:str=Form('English'),u:User=Depends(current)):
    if image.content_type not in {'image/jpeg','image/png','image/webp'}: raise HTTPException(415,'Only JPEG, PNG, and WEBP are allowed.')
    raw=await image.read()
    if not raw or len(raw)>int(os.getenv('MAX_UPLOAD_MB','8'))*1024*1024: raise HTTPException(413,'Image is empty or exceeds the upload limit.')
    return await diagnose_leaf(raw,image.content_type,language)
def post_out(p): return {'id':p.id,'title':p.title,'body':p.body,'category':p.category,'likes':p.likes or 0,'image_url':p.image_url,'created_at':p.created_at,'author':{'id':p.author.id,'name':p.author.name,'state':p.author.state},'comments':[{'id':c.id,'body':c.body,'created_at':c.created_at,'author':{'id':c.author.id,'name':c.author.name}} for c in p.comments]}
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
    image_url=p.image_url
    db.execute(delete(PostLike).where(PostLike.post_id==post_id))
    db.delete(p);db.commit()
    if image_url and image_url.startswith('/uploads/'):
        image_path=(UPLOAD_DIR/Path(image_url).name).resolve()
        if image_path.parent==UPLOAD_DIR.resolve(): image_path.unlink(missing_ok=True)
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
