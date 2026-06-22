from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
