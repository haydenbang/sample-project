# DB 스키마 정의

## ERD 개요

```
users ──< orders >── products
```

## 테이블 정의

### users

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| id | INTEGER | PK, AUTO_INCREMENT | 회원 고유 ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 로그인 아이디 |
| email | VARCHAR(100) | UNIQUE, NOT NULL | 이메일 주소 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 해시 비밀번호 |
| status | VARCHAR(20) | DEFAULT 'active' | 계정 상태 (`active` / `inactive`) |
| created_at | DATETIME | DEFAULT NOW() | 가입일시 |

### products

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| id | INTEGER | PK, AUTO_INCREMENT | 상품 고유 ID |
| name | VARCHAR(200) | NOT NULL | 상품명 |
| description | TEXT | | 상품 설명 |
| price | FLOAT | NOT NULL | 판매가 |
| stock | INTEGER | DEFAULT 0 | 재고 수량 |
| category | VARCHAR(100) | | 카테고리 |
| is_active | BOOLEAN | DEFAULT TRUE | 판매 여부 |
| created_at | DATETIME | DEFAULT NOW() | 등록일시 |

### orders

| 컬럼명 | 타입 | 제약조건 | 설명 |
|---|---|---|---|
| id | INTEGER | PK, AUTO_INCREMENT | 주문 고유 ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 주문 회원 ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 주문 상품 ID |
| quantity | INTEGER | NOT NULL | 주문 수량 |
| unit_price | FLOAT | NOT NULL | 주문 시점 단가 |
| discount_rate | FLOAT | DEFAULT 0.0 | 할인율 (0.0 ~ 1.0) |
| total_price | FLOAT | NOT NULL | 최종 결제 금액 |
| status | VARCHAR(20) | DEFAULT 'pending' | 주문 상태 (`pending` / `confirmed` / `shipped` / `cancelled`) |
| created_at | DATETIME | DEFAULT NOW() | 주문일시 |

## 인덱스

| 테이블 | 컬럼 | 종류 |
|---|---|---|
| users | email | UNIQUE |
| users | username | UNIQUE |
| orders | user_id | INDEX |
| orders | product_id | INDEX |
| orders | status | INDEX |
| orders | created_at | INDEX |

## 관계

- `orders.user_id` → `users.id` (N:1, 한 회원이 여러 주문)
- `orders.product_id` → `products.id` (N:1, 한 상품이 여러 주문에 포함)
