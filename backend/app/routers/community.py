import os, uuid
import io
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
from ..database import get_db
from ..models import User, FarmerConnection, Requirement, Post, PostLike
from ..main_auth import current

router = APIRouter(prefix="/api/community", tags=["Community"])
UPLOAD_DIR=Path(__file__).resolve().parents[2]/'uploads'

class RequirementInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=3000)
    category: str = Field(pattern="^(machinery|labor|seeds|fertilizer)$")
    state: str | None = None
    district: str | None = None
    contact_phone: str | None = Field(default=None,max_length=32)

def farmer(u):
    return {"id":u.id,"name":u.name,"state":u.state,"district":u.district,"crops":u.crops or []}

@router.get("/farmers")
def farmers(state: str | None = None, db: Session = Depends(get_db), u: User = Depends(current)):
    stmt = select(User).where(User.id != u.id)
    if state: stmt = stmt.where(User.state.ilike(f"%{state}%"))
    rows = db.scalars(stmt.order_by(User.name).limit(100)).all()
    connections = {c.target_id:c.status for c in db.scalars(select(FarmerConnection).where(FarmerConnection.requester_id==u.id))}
    return [{**farmer(x),"connection_status":connections.get(x.id,"not_connected")} for x in rows]

@router.post("/farmers/{farmer_id}/connect")
def connect(farmer_id: int, db: Session = Depends(get_db), u: User = Depends(current)):
    if farmer_id == u.id or not db.get(User, farmer_id): raise HTTPException(404,"Farmer not found.")
    c = db.scalar(select(FarmerConnection).where(FarmerConnection.requester_id==u.id, FarmerConnection.target_id==farmer_id))
    if c: return {"status":c.status}
    c=FarmerConnection(requester_id=u.id,target_id=farmer_id,status="pending"); db.add(c); db.commit()
    return {"status":"pending"}

@router.delete("/farmers/{farmer_id}/connect", status_code=204)
def cancel_connection_request(farmer_id: int, db: Session = Depends(get_db), u: User = Depends(current)):
    request=db.scalar(select(FarmerConnection).where(FarmerConnection.requester_id==u.id,FarmerConnection.target_id==farmer_id))
    if not request: raise HTTPException(404,"Connection request not found.")
    if request.status!='pending': raise HTTPException(409,"Only a pending connection request can be cancelled.")
    db.delete(request);db.commit();return Response(status_code=204)

@router.get("/requirements")
def requirements(db: Session = Depends(get_db)):
    return [{"id":r.id,"title":r.title,"description":r.description,"kind":r.kind,"category":r.kind,"state":r.state,"district":r.district,"contact_phone":r.contact_phone,"responses":r.responses,"author":farmer(r.author)} for r in db.scalars(select(Requirement).order_by(Requirement.created_at.desc()).limit(100)).all()]

@router.post("/requirements", status_code=201)
def create_requirement(payload: RequirementInput, db: Session = Depends(get_db), u: User = Depends(current)):
    values=payload.model_dump()
    r=Requirement(user_id=u.id,title=values['title'],description=values['description'],kind=values['category'],state=values['state'],district=values['district'],contact_phone=values['contact_phone'])
    db.add(r);db.commit();db.refresh(r)
    return {"id":r.id,"title":r.title,"description":r.description,"kind":r.kind,"category":r.kind,"state":r.state,"district":r.district,"contact_phone":r.contact_phone,"responses":r.responses,"author":farmer(u)}

@router.put("/requirements/{requirement_id}")
def update_requirement(requirement_id:int,payload:RequirementInput,db:Session=Depends(get_db),u:User=Depends(current)):
    r=db.get(Requirement,requirement_id)
    if not r: raise HTTPException(404,"Requirement not found.")
    if r.user_id!=u.id: raise HTTPException(403,"You can edit only your own requirement.")
    values=payload.model_dump();r.title=values['title'];r.description=values['description'];r.kind=values['category'];r.state=values['state'];r.district=values['district'];r.contact_phone=values['contact_phone'];db.commit();db.refresh(r)
    return {"id":r.id,"title":r.title,"description":r.description,"kind":r.kind,"category":r.kind,"state":r.state,"district":r.district,"contact_phone":r.contact_phone,"responses":r.responses,"author":farmer(u)}

@router.delete("/requirements/{requirement_id}",status_code=204)
def delete_requirement(requirement_id:int,db:Session=Depends(get_db),u:User=Depends(current)):
    r=db.get(Requirement,requirement_id)
    if not r: raise HTTPException(404,"Requirement not found.")
    if r.user_id!=u.id: raise HTTPException(403,"You can remove only your own requirement.")
    db.delete(r);db.commit();return Response(status_code=204)

@router.post("/requirements/{requirement_id}/respond")
def respond(requirement_id:int, db:Session=Depends(get_db), u:User=Depends(current)):
    r=db.get(Requirement,requirement_id)
    if not r: raise HTTPException(404,"Requirement not found.")
    r.responses += 1; db.commit(); return {"responses":r.responses}

@router.post("/posts/{post_id}/like")
def like(post_id:int, db:Session=Depends(get_db), u:User=Depends(current)):
    p=db.get(Post,post_id)
    if not p: raise HTTPException(404,"Post not found.")
    existing=db.scalar(select(PostLike).where(PostLike.post_id==post_id,PostLike.user_id==u.id))
    if existing:
        db.delete(existing);p.likes=max(0,(p.likes or 0)-1);liked=False
    else:
        db.add(PostLike(post_id=post_id,user_id=u.id));p.likes=(p.likes or 0)+1;liked=True
    db.commit();return {"likes":p.likes,"liked":liked}

@router.get("/posts")
def list_posts(db:Session=Depends(get_db)):
    rows=db.scalars(select(Post).order_by(Post.created_at.desc()).limit(100)).unique().all()
    return [{"id":p.id,"title":p.title,"body":p.body,"category":p.category,"likes":p.likes or 0,"image_url":p.image_url,"created_at":p.created_at,"author":farmer(p.author),"comments":[{"id":c.id,"body":c.body,"created_at":c.created_at,"author":farmer(c.author)} for c in p.comments]} for p in rows]

@router.post("/posts",status_code=201)
async def create_post(title:str=Form(...,min_length=3,max_length=180),body:str=Form(...,min_length=5,max_length=5000),category:str=Form("discussion"),image:UploadFile|None=File(None),db:Session=Depends(get_db),u:User=Depends(current)):
    if category not in {"help","experience","discussion","requirement"}: raise HTTPException(422,"Unsupported post category.")
    image_url=None
    if image and image.filename:
        if image.content_type not in {"image/jpeg","image/png","image/webp"}: raise HTTPException(415,"Post images must be JPEG, PNG, or WEBP.")
        content=await image.read()
        if len(content)>5*1024*1024: raise HTTPException(413,"Post images are limited to 5 MB.")
        try:
            with Image.open(io.BytesIO(content)) as uploaded: uploaded.verify()
        except (UnidentifiedImageError,OSError) as exc: raise HTTPException(422,"The uploaded file is not a valid image.") from exc
        suffix={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[image.content_type]
        UPLOAD_DIR.mkdir(parents=True,exist_ok=True);name=f"{uuid.uuid4().hex}{suffix}";(UPLOAD_DIR/name).write_bytes(content);image_url=f"/uploads/{name}"
    post=Post(user_id=u.id,title=title,body=body,category=category,image_url=image_url);db.add(post);db.commit();db.refresh(post)
    return {"id":post.id,"title":post.title,"body":post.body,"category":post.category,"likes":post.likes or 0,"image_url":post.image_url,"created_at":post.created_at,"author":farmer(u),"comments":[]}
