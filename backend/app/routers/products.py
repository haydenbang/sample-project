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
    """재고 상태에 따라 자동으로 상태 전환 (요구사항 FR-PRODUCT-04)."""
    if product.stock == 0 and product.status in (
        ProductStatus.ACTIVE,
        ProductStatus.LOW_STOCK,
    ):
        product.status = ProductStatus.SOLD_OUT
    elif 0 < product.stock <= LOW_STOCK_THRESHOLD and product.status == ProductStatus.ACTIVE:
        product.status = ProductStatus.LOW_STOCK
    elif product.stock > LOW_STOCK_THRESHOLD and product.status == ProductStatus.LOW_STOCK:
        product.status = ProductStatus.ACTIVE


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="상품을 찾을 수 없습니다.")
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
