export interface Product {
  id: number
  name: string
  description: string | null
  price: number
  stock: number
  category: string | null
  is_active: boolean
  created_at: string
}

export interface ProductCreate {
  name: string
  description?: string
  price: number
  stock: number
  category?: string
}

export interface ProductUpdate {
  name?: string
  description?: string
  price?: number
  stock?: number
  category?: string
  is_active?: boolean
}
