from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
