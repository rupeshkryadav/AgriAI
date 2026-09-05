import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{ROOT / 'agri_ai.db'}")
SECRET = os.getenv('JWT_SECRET', 'development-only-change-me')
pwd = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
def hash_password(value: str): return pwd.hash(value)
def verify_password(value: str, hashed: str): return pwd.verify(value, hashed)
def token_for(user_id: int):
    return jwt.encode({'sub': str(user_id), 'exp': datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES','1440')))}, SECRET, algorithm='HS256')
def decode_token(value: str):
    try: return int(jwt.decode(value, SECRET, algorithms=['HS256'])['sub'])
    except (JWTError, KeyError, ValueError): return None
