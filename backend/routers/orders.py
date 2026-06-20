from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.order import Order
from models.product import Product
from models.user import User
from schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from services.discount import calc_discount
from services.order_service import cancel_order
from common.deps import get_current_user

router = APIRouter()

VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["shipped", "cancelled"],
    "shipped": [],
    "cancelled": [],
}


@router.get("", response_model=List[OrderResponse])
def list_orders(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="주문을 찾을 수 없습니다.")
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="상품을 찾을 수 없습니다.")
    if not product.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="판매 중지된 상품입니다.")
    if product.stock < order_in.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"재고가 부족합니다. 현재 재고: {product.stock}",
        )

    discount_rate, item_total = calc_discount(
        unit_price=product.price,
        quantity=order_in.quantity,
        user_id=order_in.user_id,
    )
    total_price = item_total + order_in.shipping.delivery_fee

    order = Order(
        user_id=order_in.user_id,
        product_id=order_in.product_id,
        quantity=order_in.quantity,
        unit_price=product.price,
        discount_rate=discount_rate,
        total_price=total_price,
        status="pending",
        shipping_address=order_in.shipping.address,
        receiver_name=order_in.shipping.receiver,
        receiver_phone=order_in.shipping.phone,
        delivery_fee=order_in.shipping.delivery_fee,
    )
    product.stock -= order_in.quantity
    if product.stock == 0:
        product.is_active = False

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="주문을 찾을 수 없습니다.")

    if body.status == "cancelled":
        return cancel_order(db, order)

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{order.status}' 상태에서 '{body.status}'로 변경할 수 없습니다.",
        )
    order.status = body.status
    db.commit()
    db.refresh(order)
    return order
