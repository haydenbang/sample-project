Looking at the change event, a new `brand_id` field (nullable integer) has been added to the `Product` model. The risk identified is that if brand-specific logic needs `brand_id`, accessing it without a session refresh could cause issues.

The fix ensures that after fetching a `Product` from the database, we explicitly refresh it so the `brand_id` column (and any other newly added columns) reflects the latest state from the database, preventing stale `None` values or `AttributeError` at runtime.

```python
"""주문 생성/상태전이 비즈니스 로직."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.discount import calculate_discount

# 허용된 주문 상태 전이 (요구사항서 FR-ORDER-05)
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def create_order(db: Session, payload: OrderCreate) -> Order:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")

    items: list[OrderItem] = []
    subtotal = 0
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"상품 {line.product_id} 를 찾을 수 없습니다.",
            )
        # Refresh the product to ensure newly added columns (e.g., brand_id)
        # are populated from the database and not stale.
        db.refresh(product)
        line_total = product.price * line.quantity
        subtotal += line_total
        items.append(
            OrderItem(
                product_id=product.id,
                unit_price=product.price,
                quantity=line.quantity,
                line_total=line_total,
            )
        )

    discount = calculate_discount(subtotal, user.grade, payload.coupon_code)
    order = Order(
        user_id=user.id,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        discount_amount=discount,
        total=subtotal - discount,
        coupon_code=payload.coupon_code,
        items=items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def transition_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{order.status.value} → {new_status.value} 전이는 허용되지 않습니다.",
        )
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
```