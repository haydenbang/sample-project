export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending'

export type UserGrade = 'bronze' | 'silver' | 'gold' | 'platinum'

export interface User {
  id: number
  username: string
  email: string
  status: UserStatus
  grade: UserGrade
  created_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
}

export interface UserUpdate {
  email?: string
  status?: UserStatus
  grade?: UserGrade
}
