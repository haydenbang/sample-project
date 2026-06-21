"""회원 API 스키마. db-schema.md / models/user.py 와 동기화."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserGrade, UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    grade: UserGrade
    is_active: bool
    created_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int


class UserGradeUpdate(BaseModel):
    grade: UserGrade
