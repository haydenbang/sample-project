from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from common.auth import decode_token, Role
from models.user import User, UserStatus

bearer_scheme = HTTPBearer()

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "manager": 2,
    "admin": 3,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = int(payload.get("sub", 0))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="회원 정보를 찾을 수 없습니다.",
        )
    if user.status == UserStatus.inactive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )
    # 토큰에서 role/department 를 user 객체에 임시 주입
    user._role = payload.get("role", "viewer")
    user._department = payload.get("department", "general")
    return user


def require_role(minimum_role: Role):
    """최소 권한 레벨을 요구하는 FastAPI 의존성 팩토리."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        user_role = getattr(current_user, "_role", "viewer")
        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY.get(minimum_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{minimum_role}' 이상의 권한이 필요합니다. 현재 권한: '{user_role}'",
            )
        return current_user
    return _check
