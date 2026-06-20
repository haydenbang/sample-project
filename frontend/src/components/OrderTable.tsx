import React from 'react'
import { Order } from '../types/order'
import { updateOrderStatus } from '../hooks/useOrders'

interface OrderTableProps {
  orders: Order[]
  onStatusChange?: () => void
}

const STATUS_LABEL: Record<string, string> = {
  pending: '대기',
  confirmed: '확인',
  shipped: '배송중',
  cancelled: '취소',
}

const NEXT_STATUS: Record<string, string | null> = {
  pending: 'confirmed',
  confirmed: 'shipped',
  shipped: null,
  cancelled: null,
}

export default function OrderTable({ orders, onStatusChange }: OrderTableProps) {
  const handleAdvance = async (order: Order) => {
    const next = NEXT_STATUS[order.status]
    if (!next) return
    await updateOrderStatus(order.id, next)
    onStatusChange?.()
  }

  const handleCancel = async (order: Order) => {
    await updateOrderStatus(order.id, 'cancelled')
    onStatusChange?.()
  }

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          <th>주문ID</th>
          <th>회원ID</th>
          <th>상품ID</th>
          <th>수량</th>
          <th>단가</th>
          <th>할인율</th>
          <th>최종금액</th>
          <th>상태</th>
          <th>주문일시</th>
          <th>액션</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <tr key={order.id}>
            <td>{order.id}</td>
            <td>{order.user_id}</td>
            <td>{order.product_id}</td>
            <td>{order.quantity}</td>
            <td>{order.unit_price.toLocaleString()}원</td>
            <td>{(order.discount_rate * 100).toFixed(0)}%</td>
            <td>{order.total_price.toLocaleString()}원</td>
            <td>{STATUS_LABEL[order.status] ?? order.status}</td>
            <td>{new Date(order.created_at).toLocaleString('ko-KR')}</td>
            <td>
              {NEXT_STATUS[order.status] && (
                <button onClick={() => handleAdvance(order)} style={{ marginRight: 4 }}>
                  {STATUS_LABEL[NEXT_STATUS[order.status]!]}
                </button>
              )}
              {['pending', 'confirmed'].includes(order.status) && (
                <button onClick={() => handleCancel(order)} style={{ color: 'red' }}>
                  취소
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
