Looking at the change event, `final_amount` is a new non-nullable field added to `OrderOut`. The risk is that ORM `Order` objects returned from endpoints won't have `final_amount` computed/set, causing Pydantic serialization failures.

The fix needs to ensure `final_amount` is computed before returning `Order` objects. Since `final_amount` is likely the sum of order items' amounts, I'll add a helper to compute and attach it to the order object before returning. This is the minimal invasive fix — computing `final_amount` from order items and setting it on the ORM instance before serialization.

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
    """Ensure final_amount is set on the ORM instance before serialization.

    final_amount is computed as the sum of all order item totals.
    Falls back to 0 if no items are present.
    """
    if not hasattr(order, "final_amount") or order.final_amount is None:
        items = getattr(order, "items", None) or []
        order.final_amount = sum(
            getattr(item, "total_price", 0) or 0 for item in items
        )
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