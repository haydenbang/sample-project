import React, { useState, useCallback } from 'react'
import { useOrders } from '../hooks/useOrders'
import OrderTable from '../components/OrderTable'

const STATUS_OPTIONS = ['', 'pending', 'confirmed', 'shipped', 'cancelled']
const STATUS_LABEL: Record<string, string> = {
  '': '전체',
  pending: '대기',
  confirmed: '확인',
  shipped: '배송중',
  cancelled: '취소',
}

export default function OrdersPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const { orders, loading, error } = useOrders(
    statusFilter ? { status: statusFilter } : undefined
  )

  const handleStatusChange = useCallback(() => {
    setRefreshKey((k) => k + 1)
  }, [])

  if (loading) return <div>로딩 중...</div>
  if (error) return <div style={{ color: 'red' }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <h2>주문 관리</h2>
      <div style={{ marginBottom: 12 }}>
        <label>상태 필터: </label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <OrderTable orders={orders} onStatusChange={handleStatusChange} />
      {orders.length === 0 && <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>주문이 없습니다.</div>}
    </div>
  )
}
