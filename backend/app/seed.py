"""개발용 초기 데이터 시드."""

from sqlalchemy.orm import Session

from app.common.security import hash_password
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductStatus
from app.models.user import User, UserGrade, UserRole


def seed(db: Session) -> None:
    if db.query(User).first():
        return  # 이미 시드됨

    admin = User(
        email="admin@shopadmin.io",
        hashed_password=hash_password("admin1234"),
        full_name="관리자",
        role=UserRole.ADMIN,
        grade=UserGrade.VIP,
    )
    customer = User(
        email="user@shopadmin.io",
        hashed_password=hash_password("user1234"),
        full_name="홍길동",
        role=UserRole.VIEWER,
        grade=UserGrade.GOLD,
    )
    db.add_all([admin, customer])

    keyboard = Product(
        name="무선 키보드", category="주변기기", price=39000, stock=12, status=ProductStatus.ACTIVE, brand_id=1
    )
    mouse = Product(
        name="무선 마우스", category="주변기기", price=25000, stock=30, status=ProductStatus.ACTIVE, brand_id=1
    )
    monitor = Product(
        name="27인치 모니터", category="디스플레이", price=210000, stock=0, status=ProductStatus.SOLD_OUT, brand_id=2
    )
    db.add_all([keyboard, mouse, monitor])
    db.flush()

    order = Order(
        user_id=customer.id,
        status=OrderStatus.PAID,
        subtotal=78000,
        discount_amount=3900,
        total=74100,
        coupon_code=None,
        items=[
            OrderItem(product_id=keyboard.id, unit_price=39000, quantity=2, line_total=78000),
        ],
    )
    db.add(order)
    db.commit()