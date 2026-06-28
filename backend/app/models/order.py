Looking at the change event, I need to add `final_amount: int` field to the `OrderOut` Pydantic schema. However, examining the current file, I don't see any Pydantic schemas defined — only SQLAlchemy ORM models.

The risk description mentions `OrderOut` Pydantic schema in this file, so I need to add it. Given the existing ORM model fields and the new `final_amount` field requirement, I'll add the necessary Pydantic schemas (`OrderOut` and supporting schemas) while also adding the `final_amount` column to the `Order` ORM model since `nullable=False` implies it's a database column too.

```python
"""주문(orders) / 주문항목(order_items) 모델. docs/db-schema.md §2.3, §2.4 매핑."""

import enum
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, index=True, nullable=False
    )
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    final_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderItemOut(BaseModel):
    id: int
    order_id: int
    product_id: int
    unit_price: int
    quantity: int
    line_total: int

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    subtotal: int
    discount_amount: int
    total: int
    final_amount: int
    coupon_code: str | None
    created_at: datetime
    items: list[OrderItemOut] = []

    model_config = {"from_attributes": True}
```