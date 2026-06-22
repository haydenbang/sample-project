export interface User {
  id: number
  username: string
  email: string
  status: 'active' | 'inactive'
  phone?: string | null
  created_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
  phone?: string
}

export interface UserUpdate {
  email?: string
  status?: 'active' | 'inactive'
  phone?: string
}
