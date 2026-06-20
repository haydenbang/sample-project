import React, { useState } from 'react'
import { useProducts } from '../hooks/useProducts'
import ProductCard from '../components/ProductCard'

export default function ProductsPage() {
  const [categoryFilter, setCategoryFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined)
  const [refreshKey, setRefreshKey] = useState(0)

  const { products, loading, error } = useProducts({
    category: categoryFilter || undefined,
    is_active: activeFilter,
  })

  if (loading) return <div>로딩 중...</div>
  if (error) return <div style={{ color: 'red' }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <h2>상품 관리</h2>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <input
          placeholder="카테고리 필터"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        />
        <select
          value={activeFilter === undefined ? '' : String(activeFilter)}
          onChange={(e) => {
            const v = e.target.value
            setActiveFilter(v === '' ? undefined : v === 'true')
          }}
        >
          <option value="">전체</option>
          <option value="true">판매중</option>
          <option value="false">판매중지</option>
        </select>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            onUpdate={() => setRefreshKey((k) => k + 1)}
          />
        ))}
      </div>
      {products.length === 0 && <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>상품이 없습니다.</div>}
    </div>
  )
}
