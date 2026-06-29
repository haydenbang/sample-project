Looking at the change event, the `coupon_code` parameter in `calculate_discount` changed from a positional parameter to a keyword-only parameter. This is a 2-step indirect impact through `order_service.py` → `discount.py`.

The risks mention that API response contracts with discount values may be affected (e.g., VIP discount changing from 10% to 15%). The router itself doesn't directly call `calculate_discount`, but the response contract concern is valid.

Examining the current `orders.py` file, I don't see any direct calls to `calculate_discount` or `create_order` with `coupon_code` as a positional argument. The file itself doesn't need code logic changes since:

1. It doesn't call `calculate_discount` directly
2. The `create_order` call signature in this file (`create_order(db, payload)`) remains unchanged
3. The router just passes `payload` through

The file is functionally correct as-is. The risk described is about documentation/response contracts, but the code itself doesn't need modification. I'll preserve the file exactly as it is since no actual code change is required at this layer.

```python
"""주문 라우터. docs/api-spec.md §3 매핑."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.deps import require_roles
from app.database import get_db
from app.models.order import Order, OrderStatus
from app.models.user import UserRole
from app.schemas.order import OrderCreate, OrderListOut, OrderOut, OrderStatusUpdate
from app.services.order_service import create_order, transition_status

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=OrderListOut)
def list_orders(
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> OrderListOut:
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    total = query.count()
    items = query.order_by(Order.id.desc()).offset((page - 1) * size).limit(size).all()
    return OrderListOut(items=items, total=total, page=page, size=size)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Order:
    return create_order(db, payload)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="주문을 찾을 수 없습니다.")
    return transition_status(db, order, payload.status)
```