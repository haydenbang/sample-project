"""상품(products) 모델. docs/db-schema.md §2.2 매핑."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SOLD_OUT = "SOLD_OUT"
    ARCHIVED = "ARCHIVED"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # [도메인 추가] 신규 brands 도메인을 product 에 매핑 (scenario/domain-mapping-brand)
    # TODO(전파): schemas/product.py(ProductOut.brand_id), routers/products.py,
    #            frontend types/product.ts·ProductsPage·useProducts, seed.py, docs 에 brand 반영 필요.
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), index=True, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.DRAFT, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
