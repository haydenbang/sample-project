from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import bcrypt

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserResponse
from common.deps import get_current_user, require_role

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """신규 회원 등록 — admin 전용"""
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다.")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")

    password_hash = bcrypt.hashpw(user_in.password.encode(), bcrypt.gensalt()).decode()
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=password_hash,
        phone=user_in.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """회원 정보 수정 — admin 전용"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")

    if user_in.email is not None:
        existing = db.query(User).filter(User.email == user_in.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
        user.email = user_in.email
    if user_in.status is not None:
        user.status = user_in.status
    if user_in.phone is not None:
        user.phone = user_in.phone

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """회원 비활성화 — admin 전용"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")
    user.status = "inactive"
    db.commit()
