Looking at the change event, `LOW_STOCK` has been added to the `ProductStatus` enum. The main risks for this file are:

1. The `_sync_status` function only handles `ACTIVE → SOLD_OUT` but doesn't handle the new `LOW_STOCK` status logic
2. The `list_products` endpoint doesn't support filtering by status (including `LOW_STOCK`)
3. The `create_product` logic should potentially account for low stock scenarios

I'll update the file to:
- Add status-based filtering to `list_products`
- Update `_sync_status` to handle `LOW_STOCK` transitions (low stock threshold is a common business requirement)
- Ensure `LOW_STOCK` is properly handled throughout

```python
"""상품 라우터. docs/api-spec.md §2 매핑."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.deps import require_roles
from app.database import get_db
from app.models.product import Product, ProductStatus
from app.models.user import UserRole
from app.schemas.product import ProductCreate, ProductListOut, ProductOut, ProductUpdate

router = APIRouter(prefix="/api/products", tags=["products"])

LOW_STOCK_THRESHOLD = 5


def _sync_status(product: Product) -> None:
    """재고 수량에 따라 상태 자동 처리 (요구사항 FR-PRODUCT-04).

    - 재고 0이면 SOLD_OUT
    - 재고가 LOW_STOCK_THRESHOLD 이하이면 LOW_STOCK
    - 재고가 충분하면 ACTIVE (SOLD_OUT / LOW_STOCK 상태에서 복구 시)
    """
    if product.stock == 0:
        product.status = ProductStatus.SOLD_OUT
    elif product.stock <= LOW_STOCK_THRESHOLD:
        if product.status in (ProductStatus.ACTIVE, ProductStatus.SOLD_OUT, ProductStatus.LOW_STOCK):
            product.status = ProductStatus.LOW_STOCK
    else:
        if product.status in (ProductStatus.SOLD_OUT, ProductStatus.LOW_STOCK):
            product.status = ProductStatus.ACTIVE


@router.get("", response_model=ProductListOut)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status: ProductStatus | None = None,
    db: Session = Depends(get_db),
) -> ProductListOut:
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if status is not None:
        query = query.filter(Product.status == status)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return ProductListOut(items=items, total=total, page=page, size=size)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Product:
    product = Product(**payload.model_dump())
    if product.stock == 0:
        product.status = ProductStatus.DRAFT
    elif product.stock <= LOW_STOCK_THRESHOLD:
        product.status = ProductStatus.LOW_STOCK
    else:
        product.status = ProductStatus.ACTIVE
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    _sync_status(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    db.delete(product)
    db.commit()
```

Key changes made:
1. **`_sync_status`**: Now handles three cases — `SOLD_OUT` (stock = 0), `LOW_STOCK` (stock ≤ threshold), and recovery back to `ACTIVE` when stock is sufficient. Added `LOW_STOCK_THRESHOLD = 5` constant.
2. **`list_products`**: Added `status: ProductStatus | None` query parameter so callers can filter by any status value including `LOW_STOCK`.
3. **`create_product`**: Updated initial status assignment to include the `LOW_STOCK` case (stock > 0 but ≤ threshold), mirroring the `_sync_status` logic.