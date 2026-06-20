from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int


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
    created_at: datetime

    class Config:
        from_attributes = True
