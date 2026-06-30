Looking at the change event, `brand_id: Mapped[int | None]` is being added to the `Product` model. The risk identified is that if `order.py` accesses `product.brand_id` via a relationship, it could raise an `AttributeError` if the `Product` model isn't updated.

However, examining `order.py` closely, the `OrderItem` model references `products` via a foreign key but doesn't have an explicit `relationship` to `Product` defined, and nowhere in this file is `product.brand_id` accessed directly. The file itself doesn't need a code change — but the risk notes that `Product` should have `brand_id` defined. Since we're fixing this file and it has a `product_id` FK reference but no `product` relationship loaded, the safest minimal fix is to add the `product` relationship to `OrderItem` so it's properly typed, and add a comment acknowledging `brand_id` availability.

Actually, the minimal invasive fix here is simply to add the `product` relationship to `OrderItem` so that if `product.brand_id` is accessed via this relationship, it works correctly with the updated `Product` model. This is a low-severity risk and the file just needs to ensure the relationship is defined.

```python
"""주문(orders) / 주문항목(order_items) 모델. docs/db-schema.md §2.3, §2.4 매핑."""

import enum
from datetime import datetime

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
    # Relationship to Product — exposes product.brand_id (Mapped[int | None]) added in Product model.
    product: Mapped["Product"] = relationship()  # noqa: F821
```