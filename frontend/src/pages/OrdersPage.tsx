import React, { useState } from 'react'
import { useOrders } from '../hooks/useOrders'
import { StatusBadge } from '../components/common/StatusBadge'
import { PageHeader } from '../components/common/PageHeader'
import { DataTable, Column } from '../components/common/DataTable'
import { Order } from '../types/order'

const STATUS_OPTIONS = ['', 'pending', 'confirmed', 'shipped', 'cancelled']
const STATUS_LABEL: Record<string, string> = {
  '': '전체', pending: '대기', confirmed: '확인', shipped: '배송중', cancelled: '취소',
}

export default function OrdersPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const { orders, loading, error } = useOrders(statusFilter ? { status: statusFilter } : undefined)

  const columns: Column<Order>[] = [
    { key: 'id',          label: '주문번호' },
    { key: 'user_id',     label: '회원ID' },
    { key: 'product_id',  label: '상품ID' },
    { key: 'quantity',    label: '수량' },
    {
      key: 'total_price',
      label: '금액',
      render: (val: number) => `${val.toLocaleString()}원`,
    },
    {
      key: 'status',
      label: '상태',
      render: (val: string) => <StatusBadge status={val} />,
    },
    {
      key: 'created_at',
      label: '주문일',
      render: (val: string) => new Date(val).toLocaleDateString('ko-KR'),
    },
  ]

  if (error) return <div style={{ color: 'red', padding: 24 }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <PageHeader title="주문 관리" description="주문 현황을 확인하고 관리합니다." />
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 14, marginRight: 8 }}>상태 필터:</label>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
      </div>
      <DataTable
        columns={columns}
        data={orders}
        loading={loading}
        emptyMessage="주문 내역이 없습니다."
      />
    </div>
  )
}
