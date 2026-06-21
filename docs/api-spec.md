# API 명세서 (API Specification)

- **Base URL**: `/api`
- **인증**: `Authorization: Bearer <JWT>` (로그인 제외)
- **응답 포맷**: `application/json`

> 본 명세는 `backend/app/routers/*.py` 및 `backend/app/schemas/*.py` 와 동기화된다.
> API 스펙이 바뀌면 프론트엔드 `src/api/client.ts`, `src/hooks/*`, `src/types/*` 가 영향을 받는다.

---

## 1. Auth

### POST `/api/auth/login`
로그인 후 JWT 발급.

요청
```json
{ "email": "admin@shopadmin.io", "password": "admin1234" }
```

응답 `200`
```json
{ "access_token": "<jwt>", "token_type": "bearer", "role": "ADMIN" }
```

### GET `/api/auth/me`
현재 사용자 정보 조회. (인증 필요)

응답 `200`
```json
{ "id": 1, "email": "admin@shopadmin.io", "full_name": "관리자", "role": "ADMIN", "grade": "VIP" }
```

---

## 2. Products

### GET `/api/products`
상품 목록 조회.

| 쿼리 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `page` | int | 1 | 페이지 번호 |
| `size` | int | 20 | 페이지 크기 |
| `category` | string | - | 카테고리 필터 |

응답 `200`
```json
{
  "items": [
    { "id": 1, "name": "무선 키보드", "category": "주변기기", "price": 39000, "stock": 12, "status": "ACTIVE" }
  ],
  "total": 1, "page": 1, "size": 20
}
```

### POST `/api/products` (ADMIN/STAFF)
상품 등록.
```json
{ "name": "무선 마우스", "category": "주변기기", "price": 25000, "stock": 30 }
```

### PUT `/api/products/{id}` (ADMIN/STAFF)
### DELETE `/api/products/{id}` (ADMIN)

---

## 3. Orders

### GET `/api/orders`
주문 목록 조회.

| 쿼리 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `status` | string | - | 주문 상태 필터 |
| `page` | int | 1 | 페이지 번호 |
| `size` | int | 20 | 페이지 크기 |

응답 `200`
```json
{
  "items": [
    {
      "id": 1001, "user_id": 2, "status": "PAID",
      "subtotal": 78000, "discount_amount": 3900, "final_amount": 74100,
      "coupon_code": null,
      "items": [ { "product_id": 1, "unit_price": 39000, "quantity": 2, "line_total": 78000 } ]
    }
  ],
  "total": 1, "page": 1, "size": 20
}
```

### POST `/api/orders` (ADMIN/STAFF)
주문 생성. 서버가 합계/할인/최종금액을 계산한다.
```json
{
  "user_id": 2,
  "coupon_code": "WELCOME5",
  "items": [ { "product_id": 1, "quantity": 2 } ]
}
```

### PATCH `/api/orders/{id}/status` (ADMIN/STAFF)
주문 상태 전이. 역행 전이는 `409`.
```json
{ "status": "SHIPPED" }
```

---

## 4. Users

### GET `/api/users` (ADMIN/STAFF)
회원 목록 조회.

응답 `200`
```json
{
  "items": [
    { "id": 2, "email": "user@shopadmin.io", "full_name": "홍길동", "role": "VIEWER", "grade": "GOLD", "is_active": true }
  ],
  "total": 1, "page": 1, "size": 20
}
```

### PATCH `/api/users/{id}/grade` (ADMIN)
회원 등급 변경.
```json
{ "grade": "VIP" }
```

---

## 5. 공통 에러 응답

```json
{ "detail": "에러 메시지" }
```

| 코드 | 의미 |
|------|------|
| 400 | 잘못된 요청 |
| 401 | 인증 실패 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 상태 충돌(잘못된 상태 전이 등) |
