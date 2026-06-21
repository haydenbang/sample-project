import React, { useState } from 'react'
import { useProducts } from '../hooks/useProducts'
import { StatusBadge } from '../components/common/StatusBadge'
import { PageHeader } from '../components/common/PageHeader'
import { DataTable, Column } from '../components/common/DataTable'
import { Product } from '../types/product'

export default function ProductsPage() {
  const [categoryFilter, setCategoryFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined)
  const { products, loading, error } = useProducts({
    category: categoryFilter || undefined,
    is_active: activeFilter,
  })

  // Product는 is_active(boolean)지만 DataTable에서 status로 매핑해 StatusBadge 사용
  const asTableRow = products.map(p => ({
    ...p,
    status: p.is_active ? 'in_stock' : 'out_of_stock',
  }))

  const columns: Column<typeof asTableRow[0]>[] = [
    { key: 'id',       label: 'ID' },
    { key: 'name',     label: '상품명' },
    {
      key: 'price',
      label: '가격',
      render: (val: number) => `${val.toLocaleString()}원`,
    },
    { key: 'stock',    label: '재고' },
    { key: 'category', label: '카테고리', render: (val: string | null) => val ?? '-' },
    {
      key: 'status',
      label: '상태',
      render: (val: string) => <StatusBadge status={val} />,
    },
  ]

  if (error) return <div style={{ color: 'red', padding: 24 }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <PageHeader title="상품 관리" description="등록된 상품을 조회하고 관리합니다." />
      <div style={{ marginBottom: 12, display: 'flex', gap: 12 }}>
        <input
          placeholder="카테고리 필터"
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          style={{ padding: '4px 8px', fontSize: 14 }}
        />
        <select
          value={activeFilter === undefined ? '' : String(activeFilter)}
          onChange={e => {
            const v = e.target.value
            setActiveFilter(v === '' ? undefined : v === 'true')
          }}
        >
          <option value="">전체</option>
          <option value="true">재고있음</option>
          <option value="false">품절</option>
        </select>
      </div>
      <DataTable
        columns={columns}
        data={asTableRow}
        loading={loading}
        emptyMessage="등록된 상품이 없습니다."
      />
    </div>
  )
}
