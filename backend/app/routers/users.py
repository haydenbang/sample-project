"""회원 라우터. docs/api-spec.md §4 매핑."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.deps import require_roles
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserGradeUpdate, UserListOut, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListOut)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> UserListOut:
    query = db.query(User)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return UserListOut(items=items, total=total, page=page, size=size)


@router.patch("/{user_id}/grade", response_model=UserOut)
def update_grade(
    user_id: int,
    payload: UserGradeUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")
    user.grade = payload.grade
    db.commit()
    db.refresh(user)
    return user
