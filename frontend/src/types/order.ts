// 주문 타입. 백엔드 schemas/order.py 와 동기화.
// 응답 필드명이 바뀌면 api/client.ts, useOrders, OrdersPage 가 영향받는다.
// (scenario/api-spec-change)

export type OrderStatus =
  | "PENDING"
  | "PAID"
  | "SHIPPED"
  | "DELIVERED"
  | "CANCELLED";

export interface OrderItem {
  product_id: number;
  unit_price: number;
  quantity: number;
  line_total: number;
}

export interface Order {
  id: number;
  user_id: number;
  status: OrderStatus;
  subtotal: number;
  discount_amount: number;
  total: number;
  coupon_code: string | null;
  items: OrderItem[];
}

export interface OrderListResponse {
  items: Order[];
  total: number;
  page: number;
  size: number;
}
