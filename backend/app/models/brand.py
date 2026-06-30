"""브랜드(brands) 도메인 모델 — 상품에 매핑되는 신규 비즈니스 도메인.

scenario/domain-mapping-brand: 설계자가 상품에 브랜드 도메인을 추가하고 product 에
brand_id FK 로 매핑한다. 스키마/라우터/프론트/문서 전파는 의도적으로 미반영.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BrandTier(str, enum.Enum):
    NORMAL = "NORMAL"
    PREMIUM = "PREMIUM"


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[BrandTier] = mapped_column(Enum(BrandTier), default=BrandTier.NORMAL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
