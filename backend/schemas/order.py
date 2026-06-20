from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ShippingInfo(BaseModel):
    address: str
    receiver: str
    phone: str
    delivery_fee: float = 3000.0


class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    shipping: ShippingInfo


class OrderStatusUpdate(BaseModel):
    status: str


class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    unit_price: float
    discount_rate: float
    total_price: float
    status: str
    shipping_address: Optional[str]
    receiver_name: Optional[str]
    receiver_phone: Optional[str]
    delivery_fee: float
    created_at: datetime

    class Config:
        from_attributes = True
