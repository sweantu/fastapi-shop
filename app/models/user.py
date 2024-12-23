from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class User(BaseModel):
    id: str
    username: str
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
