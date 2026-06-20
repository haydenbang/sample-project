import React from 'react'
import { Product } from '../types/product'
import { updateProduct } from '../hooks/useProducts'

interface ProductCardProps {
  product: Product
  onUpdate?: () => void
}

export default function ProductCard({ product, onUpdate }: ProductCardProps) {
  const handleToggleActive = async () => {
    await updateProduct(product.id, { is_active: !product.is_active })
    onUpdate?.()
  }

  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderRadius: 8,
        padding: 16,
        opacity: product.is_active ? 1 : 0.5,
        maxWidth: 300,
      }}
    >
      <h4 style={{ margin: '0 0 8px' }}>{product.name}</h4>
      {product.category && (
        <span style={{ fontSize: 12, background: '#eee', padding: '2px 6px', borderRadius: 4 }}>
          {product.category}
        </span>
      )}
      <p style={{ margin: '8px 0', color: '#555', fontSize: 14 }}>{product.description}</p>
      <div style={{ fontWeight: 'bold', fontSize: 18 }}>{product.price.toLocaleString()}원</div>
      <div style={{ fontSize: 13, color: product.stock > 0 ? '#333' : 'red', margin: '4px 0' }}>
        재고: {product.stock}개 {product.stock === 0 && '(품절)'}
      </div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
        등록일: {new Date(product.created_at).toLocaleDateString('ko-KR')}
      </div>
      <button onClick={handleToggleActive}>
        {product.is_active ? '판매 중지' : '판매 재개'}
      </button>
    </div>
  )
}
