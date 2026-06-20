export interface User {
  id: number
  username: string
  email: string
  status: 'active' | 'inactive'
  created_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
}

export interface UserUpdate {
  email?: string
  status?: 'active' | 'inactive'
}
