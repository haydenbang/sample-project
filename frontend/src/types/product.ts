// 상품 타입. 백엔드 schemas/product.py 와 동기화.

export type ProductStatus = "DRAFT" | "ACTIVE" | "SOLD_OUT" | "ARCHIVED" | "LOW_STOCK";

export interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
  stock: number;
  status: ProductStatus;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  size: number;
}
