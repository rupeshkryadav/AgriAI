from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .core import decode_token

bearer = HTTPBearer()

def current(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    uid=decode_token(creds.credentials); user=db.get(User,uid) if uid else None
    if not user: raise HTTPException(401,"Invalid or expired token.")
    return user
