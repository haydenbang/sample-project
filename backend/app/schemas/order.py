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
    coupon_code: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderOut(BaseModel):
    # [API 스펙 변경] 응답 필드 total -> final_amount 로 변경. (scenario/api-spec-change)
    # 모델 속성명(order.total)은 그대로이므로 validation_alias 로 매핑한다.
    # TODO(전파): 프론트 types/order.ts, api/client.ts, OrdersPage, useOrders,
    #            그리고 tests/test_orders.py 의 응답 필드 참조를 final_amount 로 갱신해야 한다.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int
    status: OrderStatus
    subtotal: int
    discount_amount: int
    final_amount: int = Field(validation_alias="total")
    coupon_code: str | None
    items: list[OrderItemOut]


class OrderListOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    size: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
