import os
os.environ['DATABASE_URL']='sqlite:///./test_agri.db';os.environ['JWT_SECRET']='test-secret'
from fastapi.testclient import TestClient
from app.main import app
def test_registration_login_and_protection():
    with TestClient(app) as c:
        r=c.post('/api/auth/register',json={'email':'farmer@example.com','password':'securepass1','name':'Asha','crops':['Tomato']});assert r.status_code==201;r=c.get('/api/users/me');assert r.status_code==403
        token=c.post('/api/auth/login',json={'email':'farmer@example.com','password':'securepass1'}).json()['access_token'];h={'Authorization':'Bearer '+token};assert c.get('/api/users/me',headers=h).status_code==200
def test_post_authorisation_and_validation():
    with TestClient(app) as c:
        x=c.post('/api/auth/register',json={'email':'two@example.com','password':'securepass1','name':'Ravi'});h={'Authorization':'Bearer '+x.json()['access_token']};p=c.post('/api/posts',headers=h,json={'title':'Need irrigation help','body':'How do I plan irrigation?','category':'help'});assert p.status_code==201;assert c.post('/api/posts',headers=h,json={'title':'x','body':'x','category':'bad'}).status_code==422
def test_unavailable_models_are_clear_not_fake():
    with TestClient(app) as c:
        x=c.post('/api/auth/login',json={'email':'two@example.com','password':'securepass1'});h={'Authorization':'Bearer '+x.json()['access_token']};r=c.post('/api/predictions',headers=h,json={'commodity':'Tomato','state':'Karnataka','prediction_date':'2026-09-01'});assert r.status_code==503
