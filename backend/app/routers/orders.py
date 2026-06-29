Looking at the risk, the issue is that `OrderOut` now requires a `final_amount` field, but the `Order` ORM model may not have this attribute. The fix should ensure that when returning `Order` ORM objects, we compute/provide `final_amount` if it's missing from the model directly.

The safest minimal fix is to ensure the `Order` ORM objects returned have a `final_amount` attribute. Since we can't change the ORM model here, we handle this in the router by computing `final_amount` before returning, or by ensuring the response is built safely.

However, looking more carefully: the router returns `Order` ORM objects directly as `response_model=OrderOut`. The real fix needs to either:
1. Ensure the `Order` model has `final_amount`, or
2. Compute it in the router before returning

The most targeted fix for this file is to add a helper that ensures `final_amount` is populated on the ORM object before FastAPI serializes it (computing it from order items if needed), or fallback to 0 if not present.

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


def _ensure_final_amount(order: Order) -> Order:
    """final_amount가 ORM 인스턴스에 없으면 계산하여 설정합니다."""
    if not hasattr(order, "final_amount") or order.final_amount is None:
        try:
            computed = sum(
                getattr(item, "price", 0) * getattr(item, "quantity", 1)
                for item in (order.items if hasattr(order, "items") and order.items else [])
            )
        except Exception:
            computed = 0
        order.final_amount = computed
    return order


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
    items = [_ensure_final_amount(order) for order in items]
    return OrderListOut(items=items, total=total, page=page, size=size)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Order:
    order = create_order(db, payload)
    return _ensure_final_amount(order)


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
    order = transition_status(db, order, payload.status)
    return _ensure_final_amount(order)
```