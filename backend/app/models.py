from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
class User(Base):
    __tablename__='users'; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash: Mapped[str]=mapped_column(String(255)); name: Mapped[str]=mapped_column(String(120)); state: Mapped[str|None]=mapped_column(String(80)); district: Mapped[str|None]=mapped_column(String(80)); crops: Mapped[list]=mapped_column(JSON,default=list); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Prediction(Base):
    __tablename__='predictions'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); commodity: Mapped[str]=mapped_column(String(100)); state: Mapped[str]=mapped_column(String(100)); district: Mapped[str|None]=mapped_column(String(100)); market: Mapped[str|None]=mapped_column(String(100)); variety: Mapped[str|None]=mapped_column(String(100)); prediction_date: Mapped[str]=mapped_column(String(20)); predicted_price: Mapped[float]=mapped_column(Float); reference_price: Mapped[float|None]=mapped_column(Float); lower: Mapped[float|None]=mapped_column(Float); upper: Mapped[float|None]=mapped_column(Float); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Post(Base):
    __tablename__='posts'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); title: Mapped[str]=mapped_column(String(180)); body: Mapped[str]=mapped_column(Text); category: Mapped[str]=mapped_column(String(50)); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); author=relationship('User'); comments=relationship('Comment',cascade='all, delete-orphan')
class Comment(Base):
    __tablename__='comments'; id: Mapped[int]=mapped_column(primary_key=True); post_id: Mapped[int]=mapped_column(ForeignKey('posts.id')); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); body: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); author=relationship('User')
class Notification(Base):
    __tablename__='notifications'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); message: Mapped[str]=mapped_column(String(300)); read: Mapped[bool]=mapped_column(default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
