# 변경 영향도 데모 시나리오 (Change Impact Scenarios)

본 문서는 `change-propagator` 데모를 위한 시나리오 브랜치와 각 변경이 일으키는 **파급(영향) 범위**를 정리한다.
각 브랜치는 `main` 대비 의도적인 변경을 담고 있으며, 일부 시나리오는 "함께 바뀌어야 하지만 아직 안 바뀐" 파일을 남겨 영향 분석 대상이 되도록 설계되었다.

| # | 브랜치 | 변경 트리거 | 함께 영향받는 파일(전파 대상) |
|---|--------|-------------|-------------------------------|
| 1 | `scenario/req-change` | 요구사항서에 신규 요구사항 추가 | 미구현된 backend/frontend (요구사항↔구현 추적) |
| 2 | `scenario/db-schema-change` | `users`에 `phone` 컬럼 추가 | model → schema → router → docs → frontend type/page |
| 3 | `scenario/shared-component-change` | 공통 `StatusBadge` props 변경 | 이를 사용하는 Products/Orders/Users 전 페이지 |
| 4 | `scenario/api-spec-change` | `/api/orders` 응답 필드 변경 | api client → hooks → 페이지, 연관 백엔드 스키마 |
| 5 | `scenario/env-var-change` | 신규 환경변수 `PAYMENT_API_KEY` 추가 | config → Dockerfile → docker-compose → CI → .env.example |
| 6 | `scenario/discount-policy-change` | 할인 서비스 시그니처/규칙 변경 | order_service → 테스트 → 프론트 금액 표시 |

---

## 1. `scenario/req-change` — 요구사항 변경/추가

- **변경**: `docs/requirements.md`에 `FR-PRODUCT-06: 재고 부족(임계치 이하) 알림` 신규 요구사항 추가.
- **영향**: 요구사항은 추가됐으나 구현(backend 알림 로직, frontend 배지)은 미반영 → "요구사항 대비 구현 누락" 추적 대상.
- **데모 포인트**: 문서 변경만으로도 어떤 코드가 새로 필요한지 식별.

## 2. `scenario/db-schema-change` — DB 스키마 변경

- **변경**: `users` 테이블에 `phone VARCHAR(20)` 추가 (`db-schema.md` + `models/user.py`).
- **영향**: `schemas/user.py`(응답/요청), `routers/users.py`, 프론트 `types/user.ts`, `UsersPage`, `api-spec.md`.
- **데모 포인트**: 한 모델 컬럼 추가가 백→프론트→문서까지 전파.

## 3. `scenario/shared-component-change` — 공통 컴포넌트 변경

- **변경**: `StatusBadge`의 prop을 `status` → `value` + 필수 `kind` 로 변경.
- **영향**: `StatusBadge`를 import하는 모든 페이지(Products/Orders/Users)와 테스트.
- **데모 포인트**: 공통 컴포넌트 1개 수정 → N개 사용처 동시 영향.

## 4. `scenario/api-spec-change` — API 스펙 변경

- **변경**: `/api/orders` 응답의 `total` → `final_amount` 로 필드명 변경.
- **영향**: 백엔드 `schemas/order.py`, 프론트 `types/order.ts`, `api/client.ts`, `useOrders`, `OrdersPage`, `api-spec.md`.
- **데모 포인트**: 응답 계약(contract) 변경이 소비자 코드 전반에 전파.

## 5. `scenario/env-var-change` — 배포 환경변수 추가

- **변경**: 결제 연동용 `PAYMENT_API_KEY` 환경변수 추가.
- **영향**: `config.py`, `backend/Dockerfile`, `docker-compose.yml`, `ci/ci.yml`, `backend/.env.example`.
- **데모 포인트**: 코드가 요구하는 신규 env가 배포 스크립트 전반에 누락 없이 반영됐는지 점검.

## 6. `scenario/discount-policy-change` — 공통 서비스 변경

- **변경**: `calculate_discount()` 시그니처 변경 및 VIP 할인율 10%→15% 상향.
- **영향**: `services/order_service.py`, `tests/test_discount.py`, 프론트 금액 표시 로직.
- **데모 포인트**: 비즈니스 규칙(공통 서비스) 변경이 호출부·테스트·UI로 전파.
