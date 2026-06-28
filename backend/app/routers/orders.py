Looking at the change event, `OrderOut` now requires a `final_amount` field (non-nullable int). The risk is that `Order` model objects returned from the endpoints may not have this field populated, causing Pydantic `ValidationError` at runtime.

The fix needs to ensure `final_amount` is computed and available when `Order` objects are serialized into `OrderOut`. Since the field is being added to the schema, I need to ensure the router handles this properly. The most targeted fix is to ensure the responses include `final_amount` by computing it if necessary before returning, or by ensuring the ORM model has it. Since the router constructs responses from `Order` ORM objects, and `OrderOut` now requires `final_amount`, I need to make sure the field is populated on the returned objects.

The safest minimal fix at the router level is to ensure `final_amount` is set on the order before returning it (e.g., computed from order items total), but without knowing the exact business logic, the correct approach is to ensure `final_amount` is available on the `Order` model. At the router level, I'll add a helper to compute/assign `final_amount` if it's not already set, or simply ensure it's passed through. Given the router just returns ORM objects, the fix should ensure `final_amount` is populated.

The minimal invasive fix: compute `final_amount` from the order's items (if not already set) before returning in each endpoint.

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
    """Ensure final_amount is populated on the Order instance before serialization."""
    if order.final_amount is None:
        order.final_amount = int(
            sum(item.unit_price * item.quantity for item in order.items)
            if order.items
            else 0
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