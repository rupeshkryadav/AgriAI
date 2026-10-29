from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
class User(Base):
    __tablename__='users'; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash: Mapped[str]=mapped_column(String(255)); name: Mapped[str]=mapped_column(String(120)); state: Mapped[str|None]=mapped_column(String(80)); district: Mapped[str|None]=mapped_column(String(80)); crops: Mapped[list]=mapped_column(JSON,default=list); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Prediction(Base):
    __tablename__='predictions'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); commodity: Mapped[str]=mapped_column(String(100)); state: Mapped[str]=mapped_column(String(100)); district: Mapped[str|None]=mapped_column(String(100)); market: Mapped[str|None]=mapped_column(String(100)); variety: Mapped[str|None]=mapped_column(String(100)); prediction_date: Mapped[str]=mapped_column(String(20)); predicted_price: Mapped[float]=mapped_column(Float); reference_price: Mapped[float|None]=mapped_column(Float); lower: Mapped[float|None]=mapped_column(Float); upper: Mapped[float|None]=mapped_column(Float); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Post(Base):
	__tablename__='posts'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); title: Mapped[str]=mapped_column(String(180)); body: Mapped[str]=mapped_column(Text); category: Mapped[str]=mapped_column(String(50)); image_url: Mapped[str|None]=mapped_column(String(500),nullable=True); likes: Mapped[int]=mapped_column(Integer,default=0); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); author=relationship('User'); comments=relationship('Comment',cascade='all, delete-orphan')

class PostLike(Base):
	__tablename__='post_likes'; __table_args__=(UniqueConstraint('post_id','user_id',name='uq_post_like_user'),); id: Mapped[int]=mapped_column(primary_key=True); post_id: Mapped[int]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE'),index=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Comment(Base):
    __tablename__='comments'; id: Mapped[int]=mapped_column(primary_key=True); post_id: Mapped[int]=mapped_column(ForeignKey('posts.id')); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); body: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); author=relationship('User')
class Notification(Base):
    __tablename__='notifications'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); message: Mapped[str]=mapped_column(String(300)); read: Mapped[bool]=mapped_column(default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class FarmerConnection(Base):
	__tablename__='farmer_connections'; id: Mapped[int]=mapped_column(primary_key=True); requester_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); target_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); status: Mapped[str]=mapped_column(String(20),default='pending'); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class Requirement(Base):
	__tablename__='requirements'; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id')); title: Mapped[str]=mapped_column(String(160)); description: Mapped[str]=mapped_column(Text); kind: Mapped[str]=mapped_column(String(30)); state: Mapped[str|None]=mapped_column(String(80)); district: Mapped[str|None]=mapped_column(String(80)); contact_phone: Mapped[str|None]=mapped_column(String(32),nullable=True); responses: Mapped[int]=mapped_column(Integer,default=0); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); author=relationship('User')

class PlaceCoordinate(Base):
	__tablename__='place_coordinates'; place: Mapped[str]=mapped_column(String(320),primary_key=True); latitude: Mapped[float]=mapped_column(Float); longitude: Mapped[float]=mapped_column(Float); source: Mapped[str]=mapped_column(String(100),default='verified coordinate'); state: Mapped[str|None]=mapped_column(String(100),nullable=True,index=True); district: Mapped[str|None]=mapped_column(String(100),nullable=True); updated_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class MandiStateSync(Base):
	__tablename__='mandi_state_sync'; state: Mapped[str]=mapped_column(String(100),primary_key=True); records_count: Mapped[int]=mapped_column(Integer,default=0); synced_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)

class MandiRecord(Base):
    __tablename__='mandi_records'
    __table_args__=(UniqueConstraint('commodity','variety','state','district','market','arrival_date',name='uq_mandi_observation'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    commodity: Mapped[str]=mapped_column(String(120),index=True)
    variety: Mapped[str|None]=mapped_column(String(120),nullable=True)
    state: Mapped[str]=mapped_column(String(100),index=True)
    district: Mapped[str]=mapped_column(String(100),index=True)
    market: Mapped[str]=mapped_column(String(160))
    min_price: Mapped[float|None]=mapped_column(Float,nullable=True)
    max_price: Mapped[float|None]=mapped_column(Float,nullable=True)
    modal_price: Mapped[float]=mapped_column(Float)
    arrival_date: Mapped[str]=mapped_column(String(32),index=True)
    lat: Mapped[float|None]=mapped_column(Float,nullable=True)
    lon: Mapped[float|None]=mapped_column(Float,nullable=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
