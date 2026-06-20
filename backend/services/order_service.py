from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.order import Order
from models.product import Product
from schemas.order import OrderCreate
from services.discount import calc_discount


def create_order(db: Session, order_in: OrderCreate) -> Order:
    """주문 생성 — 재고 확인, 할인 계산, 재고 차감."""
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

    discount_rate, total_price = calc_discount(
        unit_price=product.price,
        quantity=order_in.quantity,
        user_id=order_in.user_id,
    )

    order = Order(
        user_id=order_in.user_id,
        product_id=order_in.product_id,
        quantity=order_in.quantity,
        unit_price=product.price,
        discount_rate=discount_rate,
        total_price=total_price,
        status="pending",
    )
    product.stock -= order_in.quantity
    if product.stock == 0:
        product.is_active = False

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: Order) -> Order:
    """주문 취소 — 재고 원복."""
    if order.status not in ("pending", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="취소 가능한 상태가 아닙니다.",
        )
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if product:
        product.stock += order.quantity
        product.is_active = True

    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return order
