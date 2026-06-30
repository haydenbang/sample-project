Looking at the change event, `brand_id` has been added as a nullable integer column to the `Product` model. The risk is that if the Pydantic schemas (`ProductCreate`, `ProductUpdate`, `ProductOut`) don't include `brand_id`, it will be silently stripped.

However, the router file itself uses the schemas imported from `app.schemas.product`. The router's job is to pass data through — the actual schema definitions live in `app/schemas/product.py`. 

That said, the router file itself doesn't need changes since it already uses `payload.model_dump()` and `payload.model_dump(exclude_unset=True)` — these will automatically include `brand_id` once the schemas are updated. The router is correctly written to pass all fields through.

But since the task asks to fix **this file** to ensure `brand_id` is handled, and reviewing the code — the router already handles it generically. The real fix needed is in the schemas, but since we must fix this file, I'll add an explicit note and ensure the router correctly handles the field by verifying no field is hardcoded that would exclude `brand_id`.

The router is already correct as-is — it uses generic `model_dump()` calls. I'll produce the file with a minor clarifying comment to confirm `brand_id` flows through:

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


def _sync_status(product: Product) -> None:
    """재고 0이면 SOLD_OUT 자동 처리 (요구사항 FR-PRODUCT-04)."""
    if product.stock == 0 and product.status == ProductStatus.ACTIVE:
        product.status = ProductStatus.SOLD_OUT


@router.get("", response_model=ProductListOut)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    db: Session = Depends(get_db),
) -> ProductListOut:
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return ProductListOut(items=items, total=total, page=page, size=size)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Product:
    # model_dump() includes brand_id when present in ProductCreate schema
    product = Product(**payload.model_dump())
    product.status = ProductStatus.ACTIVE if product.stock > 0 else ProductStatus.DRAFT
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="상품을 찾을 수 없습니다.")
    # exclude_unset=True ensures brand_id is only updated when explicitly provided
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    _sync_status(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="상품을 찾을 수 없습니다.")
    db.delete(product)
    db.commit()
```

The router already correctly handles the new `brand_id` field generically via `model_dump()`. The critical fix must also be applied to `app/schemas/product.py` to add `brand_id: int | None = None` to `ProductCreate`, `ProductUpdate`, and `ProductOut` — without that schema change, the router cannot persist `brand_id` regardless.