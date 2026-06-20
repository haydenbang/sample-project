from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base
import datetime


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_rate = Column(Float, default=0.0)   # 0.0 ~ 1.0
    total_price = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    # 배송 정보
    shipping_address = Column(String(500), nullable=True)
    receiver_name = Column(String(100), nullable=True)
    receiver_phone = Column(String(20), nullable=True)
    delivery_fee = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
