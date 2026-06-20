import { useState, useEffect } from 'react'
import axios from 'axios'
import { User, UserCreate, UserUpdate } from '../types/user'

const API_BASE = 'http://localhost:8000/api/v1'

function getAuthHeader() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useUsers(statusFilter?: string) {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = statusFilter ? { status: statusFilter } : {}
    axios
      .get<User[]>(`${API_BASE}/users`, { headers: getAuthHeader(), params })
      .then((res) => setUsers(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '회원 목록 조회 실패'))
      .finally(() => setLoading(false))
  }, [statusFilter])

  return { users, loading, error }
}

export function useUser(userId: number) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<User>(`${API_BASE}/users/${userId}`, { headers: getAuthHeader() })
      .then((res) => setUser(res.data))
      .catch((err) => setError(err.response?.data?.detail ?? '회원 조회 실패'))
      .finally(() => setLoading(false))
  }, [userId])

  return { user, loading, error }
}

export async function createUser(data: UserCreate): Promise<User> {
  const res = await axios.post<User>(`${API_BASE}/users`, data, {
    headers: getAuthHeader(),
  })
  return res.data
}

export async function updateUser(userId: number, data: UserUpdate): Promise<User> {
  const res = await axios.patch<User>(`${API_BASE}/users/${userId}`, data, {
    headers: getAuthHeader(),
  })
  return res.data
}
