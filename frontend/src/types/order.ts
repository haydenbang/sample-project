export interface ShippingInfo {
  shipping_address: string
  receiver_name: string
  receiver_phone: string
}

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
  shipping_address?: string
  receiver_name?: string
  receiver_phone?: string
  delivery_fee: number
}

export interface OrderCreate {
  user_id: number
  product_id: number
  quantity: number
  shipping: ShippingInfo
}
