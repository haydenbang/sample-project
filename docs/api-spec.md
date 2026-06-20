# API 명세

## 기본 정보

- Base URL: `http://localhost:8000/api/v1`
- 인증 방식: Bearer JWT Token
- Content-Type: `application/json`

---

## 인증 API

### POST /auth/login

로그인 후 JWT 토큰 발급

**Request**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 회원 API

### GET /users

회원 목록 조회

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| skip | integer | N | 오프셋 (기본값: 0) |
| limit | integer | N | 조회 건수 (기본값: 20) |
| status | string | N | 상태 필터 (`active` / `inactive`) |

**Response 200**
```json
[
  {
    "id": 1,
    "username": "user01",
    "email": "user01@example.com",
    "status": "active",
    "created_at": "2024-01-15T09:00:00"
  }
]
```

### GET /users/{user_id}

회원 상세 조회

**Response 200**
```json
{
  "id": 1,
  "username": "user01",
  "email": "user01@example.com",
  "status": "active",
  "created_at": "2024-01-15T09:00:00"
}
```

### POST /users

회원 등록

**Request**
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword"
}
```

**Response 201**
```json
{
  "id": 42,
  "username": "newuser",
  "email": "newuser@example.com",
  "status": "active",
  "created_at": "2024-06-21T10:30:00"
}
```

### PATCH /users/{user_id}

회원 정보 수정

**Request**
```json
{
  "email": "updated@example.com",
  "status": "inactive"
}
```

**Response 200**: UserResponse 참조

---

## 주문 API

### GET /orders

주문 목록 조회

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| skip | integer | N | 오프셋 |
| limit | integer | N | 조회 건수 |
| status | string | N | 주문 상태 필터 |
| user_id | integer | N | 특정 회원 주문만 조회 |

**Response 200**
```json
[
  {
    "id": 1,
    "user_id": 3,
    "product_id": 7,
    "quantity": 5,
    "unit_price": 29900.0,
    "discount_rate": 0.05,
    "total_price": 142025.0,
    "status": "confirmed",
    "created_at": "2024-06-20T14:22:00"
  }
]
```

### GET /orders/{order_id}

주문 상세 조회

**Response 200**: OrderResponse 참조

### POST /orders

주문 생성

**Request**
```json
{
  "user_id": 3,
  "product_id": 7,
  "quantity": 5
}
```

**Response 201**: OrderResponse 참조

### PATCH /orders/{order_id}/status

주문 상태 변경

**Request**
```json
{
  "status": "confirmed"
}
```

**Response 200**: OrderResponse 참조

---

## 상품 API

### GET /products

상품 목록 조회

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| skip | integer | N | 오프셋 |
| limit | integer | N | 조회 건수 |
| category | string | N | 카테고리 필터 |
| is_active | boolean | N | 판매 여부 필터 |

**Response 200**
```json
[
  {
    "id": 7,
    "name": "프리미엄 볼펜 세트",
    "description": "부드러운 필기감의 볼펜 10자루 세트",
    "price": 29900.0,
    "stock": 150,
    "category": "문구",
    "is_active": true,
    "created_at": "2024-03-10T08:00:00"
  }
]
```

### GET /products/{product_id}

상품 상세 조회

**Response 200**: ProductResponse 참조

### POST /products

상품 등록

**Request**
```json
{
  "name": "신상품",
  "description": "상품 설명",
  "price": 15000.0,
  "stock": 100,
  "category": "생활용품"
}
```

**Response 201**: ProductResponse 참조

### PATCH /products/{product_id}

상품 정보 수정

**Request** (부분 업데이트)
```json
{
  "price": 12000.0,
  "stock": 80
}
```

**Response 200**: ProductResponse 참조

---

## 공통 에러 응답

| 상태 코드 | 설명 |
|---|---|
| 400 | Bad Request - 잘못된 요청 파라미터 |
| 401 | Unauthorized - 인증 토큰 없음 또는 만료 |
| 403 | Forbidden - 권한 없음 |
| 404 | Not Found - 리소스 없음 |
| 409 | Conflict - 중복 데이터 (이메일, 아이디) |
| 422 | Unprocessable Entity - 유효성 검사 실패 |
| 500 | Internal Server Error |

**에러 응답 형식**
```json
{
  "detail": "해당 회원을 찾을 수 없습니다."
}
```
