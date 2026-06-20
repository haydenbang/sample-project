from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class UserGrade(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    status: Optional[UserStatus] = None
    grade: Optional[UserGrade] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: UserStatus
    grade: UserGrade
    created_at: datetime

    class Config:
        from_attributes = True
