from pydantic import BaseModel, EmailStr, Field
class Register(BaseModel): email: EmailStr; password: str=Field(min_length=8,max_length=72); name: str=Field(min_length=2,max_length=120); state: str|None=None; district: str|None=None; crops:list[str]=[]
class Login(BaseModel): email: EmailStr; password:str
class Profile(BaseModel): name:str=Field(min_length=2,max_length=120); state:str|None=None; district:str|None=None; crops:list[str]=[]
class PriceRequest(BaseModel): commodity:str; state:str; district:str|None=None; market:str|None=None; variety:str|None=None; prediction_date:str
class PostInput(BaseModel): title:str=Field(min_length=3,max_length=180); body:str=Field(min_length=5,max_length=5000); category:str=Field(pattern='^(help|experience|discussion|requirement)$')
class CommentInput(BaseModel): body:str=Field(min_length=1,max_length=2000)
