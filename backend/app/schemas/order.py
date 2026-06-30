"""주문 API 스키마 (응답 계약).

`total` 등 필드명을 바꾸면 프론트 types/order.ts, api/client.ts, useOrders 가 영향받는다.
(변경 영향도 데모: scenario/api-spec-change)
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    unit_price: int
    quantity: int
    line_total: int


class OrderCreate(BaseModel):
    user_id: int
    # [정책 변경] 쿠폰 코드를 필수(optional→required)로 강화 (scenario/nullable-tighten)
    # TODO(전파): FE types/order.ts·api/client.ts·useOrders·OrdersPage 폼, mock,
    #            docs/api-spec.md 를 필수 필드로 갱신해야 한다. (미반영 시 FE가 null 전송 → 422)
    coupon_code: str = Field(min_length=1)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    subtotal: int
    discount_amount: int
    total: int
    coupon_code: str | None
    items: list[OrderItemOut]


class OrderListOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    size: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
