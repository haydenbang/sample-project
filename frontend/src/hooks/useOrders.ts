import { useState, useEffect } from 'react'
import axios from 'axios'
import { Order, OrderCreate } from '../types/order'

const API_BASE = 'http://localhost:8000/api/v1'

function getAuthHeader() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useOrders(params?: { status?: string; user_id?: number }) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Order[]>(`${API_BASE}/orders`, { headers: getAuthHeader(), params })
      .then((res) => setOrders(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '주문 목록 조회 실패'))
      .finally(() => setLoading(false))
  }, [params?.status, params?.user_id])

  return { orders, loading, error }
}

export function useOrder(orderId: number) {
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Order>(`${API_BASE}/orders/${orderId}`, { headers: getAuthHeader() })
      .then((res) => setOrder(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '주문 조회 실패'))
      .finally(() => setLoading(false))
  }, [orderId])

  return { order, loading, error }
}

export async function createOrder(data: OrderCreate): Promise<Order> {
  const res = await axios.post<Order>(`${API_BASE}/orders`, data, {
    headers: getAuthHeader(),
  })
  return res.data
}

export async function updateOrderStatus(orderId: number, status: string): Promise<Order> {
  const res = await axios.patch<Order>(
    `${API_BASE}/orders/${orderId}/status`,
    { status },
    { headers: getAuthHeader() }
  )
  return res.data
}
