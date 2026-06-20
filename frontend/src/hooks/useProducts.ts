import { useState, useEffect } from 'react'
import axios from 'axios'
import { Product, ProductCreate, ProductUpdate } from '../types/product'

const API_BASE = 'http://localhost:8000/api/v1'

function getAuthHeader() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useProducts(params?: { category?: string; is_active?: boolean }) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Product[]>(`${API_BASE}/products`, { headers: getAuthHeader(), params })
      .then((res) => setProducts(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '상품 목록 조회 실패'))
      .finally(() => setLoading(false))
  }, [params?.category, params?.is_active])

  return { products, loading, error }
}

export function useProduct(productId: number) {
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Product>(`${API_BASE}/products/${productId}`, { headers: getAuthHeader() })
      .then((res) => setProduct(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '상품 조회 실패'))
      .finally(() => setLoading(false))
  }, [productId])

  return { product, loading, error }
}

export async function createProduct(data: ProductCreate): Promise<Product> {
  const res = await axios.post<Product>(`${API_BASE}/products`, data, {
    headers: getAuthHeader(),
  })
  return res.data
}

export async function updateProduct(productId: number, data: ProductUpdate): Promise<Product> {
  const res = await axios.patch<Product>(`${API_BASE}/products/${productId}`, data, {
    headers: getAuthHeader(),
  })
  return res.data
}
