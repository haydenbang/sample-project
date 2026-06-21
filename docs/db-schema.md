# DB 스키마 정의서 (Database Schema Specification)

- **프로젝트명**: ShopAdmin 쇼핑몰 백오피스
- **문서 버전**: v1.0
- **최종 수정일**: 2026-06-21
- **DBMS**: 개발 SQLite / 운영 PostgreSQL 가정
- **ORM**: SQLAlchemy

> 본 문서의 컬럼 정의는 `backend/app/models/*.py` 와 1:1로 매핑된다.
> 스키마가 변경되면 모델, Pydantic 스키마, 라우터, 프론트엔드 타입이 함께 영향을 받는다.

---

## 1. ERD 개요

```
users (1) ────< (N) orders (1) ────< (N) order_items >──── (1) products
```

- 한 회원(`users`)은 여러 주문(`orders`)을 가진다.
- 한 주문(`orders`)은 여러 주문항목(`order_items`)을 가진다.
- 주문항목(`order_items`)은 하나의 상품(`products`)을 참조한다.

---

## 2. 테이블 정의

### 2.1 `users` — 회원

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTO | 회원 식별자 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 로그인 이메일 |
| `hashed_password` | VARCHAR(255) | NOT NULL | 해시된 비밀번호 |
| `full_name` | VARCHAR(100) | NOT NULL | 회원 이름 |
| `phone` | VARCHAR(20) | NULL | 휴대폰 번호 **(신규 컬럼)** |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT `'VIEWER'` | 권한: ADMIN/STAFF/VIEWER |
| `grade` | VARCHAR(20) | NOT NULL, DEFAULT `'BRONZE'` | 등급: BRONZE/SILVER/GOLD/VIP |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT `true` | 활성 여부 |
| `created_at` | DATETIME | NOT NULL, DEFAULT now | 생성 시각 |

### 2.2 `products` — 상품

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTO | 상품 식별자 |
| `name` | VARCHAR(200) | NOT NULL | 상품명 |
| `category` | VARCHAR(50) | NOT NULL | 카테고리 |
| `price` | INTEGER | NOT NULL, CHECK >= 0 | 단가(원) |
| `stock` | INTEGER | NOT NULL, DEFAULT 0 | 재고 수량 |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `'DRAFT'` | DRAFT/ACTIVE/SOLD_OUT/ARCHIVED |
| `created_at` | DATETIME | NOT NULL, DEFAULT now | 생성 시각 |

### 2.3 `orders` — 주문

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTO | 주문 식별자 |
| `user_id` | INTEGER | FK → users.id, NOT NULL | 주문 회원 |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `'PENDING'` | PENDING/PAID/SHIPPED/DELIVERED/CANCELLED |
| `subtotal` | INTEGER | NOT NULL | 할인 전 합계 |
| `discount_amount` | INTEGER | NOT NULL, DEFAULT 0 | 적용 할인액 |
| `total` | INTEGER | NOT NULL | 최종 결제 금액 |
| `coupon_code` | VARCHAR(50) | NULL | 사용 쿠폰 코드 |
| `created_at` | DATETIME | NOT NULL, DEFAULT now | 생성 시각 |

### 2.4 `order_items` — 주문 항목

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTO | 항목 식별자 |
| `order_id` | INTEGER | FK → orders.id, NOT NULL | 소속 주문 |
| `product_id` | INTEGER | FK → products.id, NOT NULL | 상품 |
| `unit_price` | INTEGER | NOT NULL | 주문 시점 단가 |
| `quantity` | INTEGER | NOT NULL, CHECK > 0 | 수량 |
| `line_total` | INTEGER | NOT NULL | unit_price × quantity |

---

## 3. 인덱스

| 테이블 | 인덱스 | 컬럼 |
|--------|--------|------|
| users | `ix_users_email` | email (UNIQUE) |
| products | `ix_products_category` | category |
| products | `ix_products_status` | status |
| orders | `ix_orders_user_id` | user_id |
| orders | `ix_orders_status` | status |
| order_items | `ix_order_items_order_id` | order_id |

---

## 4. 열거형(Enum) 정의

| Enum | 값 |
|------|-----|
| `UserRole` | ADMIN, STAFF, VIEWER |
| `UserGrade` | BRONZE, SILVER, GOLD, VIP |
| `ProductStatus` | DRAFT, ACTIVE, SOLD_OUT, ARCHIVED |
| `OrderStatus` | PENDING, PAID, SHIPPED, DELIVERED, CANCELLED |

> Enum 변경 시 백엔드 모델/스키마와 프론트엔드 `src/types/*.ts`, `StatusBadge` 매핑이 함께 변경되어야 한다.
