export interface Order {
  id: number
  user_id: number
  product_id: number
  quantity: number
  unit_price: number
  discount_rate: number
  total_price: number
  status: 'pending' | 'confirmed' | 'shipped' | 'cancelled'
  created_at: string
}

export interface OrderCreate {
  user_id: number
  product_id: number
  quantity: number
}
