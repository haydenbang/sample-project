# 기능 요구사항서 (Functional Requirements Specification)

- **프로젝트명**: ShopAdmin — 쇼핑몰 백오피스(Back-office) 샘플 프로젝트
- **문서 버전**: v1.0
- **최종 수정일**: 2026-06-21
- **목적**: 본 문서는 `change-propagator` 앱이 변경 영향도 분석 데모에 활용하는 샘플 프로젝트의 기능 요구사항을 정의한다.

---

## 1. 개요

ShopAdmin은 쇼핑몰 운영자가 **상품 / 주문 / 회원**을 관리하는 SPA(Single Page Application) 백오피스다.
프론트엔드(React)와 백엔드(FastAPI)로 구성되며, REST API로 통신한다.

### 1.1 시스템 구성

| 영역 | 기술 스택 |
|------|-----------|
| Frontend | Vite + React + TypeScript |
| Backend | FastAPI + SQLAlchemy (Python) |
| DB | SQLite(개발) / PostgreSQL(운영 가정) |
| 배포 | Docker, docker-compose |
| CI/CD | GitHub Actions |

### 1.2 사용자 역할 (Role)

| 역할 | 설명 | 권한 |
|------|------|------|
| `ADMIN` | 최고 관리자 | 모든 기능 |
| `STAFF` | 운영 담당자 | 상품/주문 조회·수정, 회원 조회 |
| `VIEWER` | 조회 전용 | 모든 조회만 가능 |

---

## 2. 기능 요구사항

### FR-AUTH: 인증/인가

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-AUTH-01 | 사용자는 이메일/비밀번호로 로그인하고 JWT 액세스 토큰을 발급받는다. | High |
| FR-AUTH-02 | 보호된 API는 `Authorization: Bearer <token>` 헤더를 검증한다. | High |
| FR-AUTH-03 | 토큰에는 사용자 식별자와 역할(role)이 포함된다. | High |
| FR-AUTH-04 | 역할 기반으로 쓰기 작업(생성/수정/삭제) 접근을 제어한다. | Medium |

### FR-PRODUCT: 상품 관리

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-PRODUCT-01 | 상품 목록을 페이지네이션으로 조회한다. | High |
| FR-PRODUCT-02 | 상품을 등록/수정/삭제한다. | High |
| FR-PRODUCT-03 | 상품은 `DRAFT / ACTIVE / SOLD_OUT / ARCHIVED` 상태를 가진다. | High |
| FR-PRODUCT-04 | 재고(`stock`)가 0이면 상태가 자동으로 `SOLD_OUT`이 된다. | Medium |
| FR-PRODUCT-05 | 카테고리별로 상품을 필터링한다. | Low |

### FR-ORDER: 주문 관리

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-ORDER-01 | 주문 목록을 상태별로 조회한다. | High |
| FR-ORDER-02 | 주문은 `PENDING / PAID / SHIPPED / DELIVERED / CANCELLED` 상태를 가진다. | High |
| FR-ORDER-03 | 주문 생성 시 상품 단가·수량으로 합계를 계산한다. | High |
| FR-ORDER-04 | 할인 정책(쿠폰/등급)에 따라 최종 결제 금액을 산출한다. | High |
| FR-ORDER-05 | 주문 상태 전이는 정해진 순서를 따른다(역행 불가). | Medium |

### FR-USER: 회원 관리

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-USER-01 | 회원 목록을 조회한다. | High |
| FR-USER-02 | 회원 등급(`BRONZE / SILVER / GOLD / VIP`)을 관리한다. | Medium |
| FR-USER-03 | 회원 등급에 따라 주문 할인율이 달라진다. | Medium |

### FR-DASH: 대시보드(공통)

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-DASH-01 | 모든 목록 화면은 공통 컴포넌트(`PageHeader`, `DataTable`, `StatusBadge`)를 사용한다. | High |
| FR-DASH-02 | 상태 값은 `StatusBadge` 공통 컴포넌트로 일관되게 표시한다. | Medium |

---

## 3. 할인 정책 (비즈니스 규칙)

최종 결제 금액 = `상품 합계 - 등급 할인 - 쿠폰 할인` (음수 방지, 0 하한)

| 회원 등급 | 등급 할인율 |
|-----------|-------------|
| BRONZE | 0% |
| SILVER | 3% |
| GOLD | 5% |
| VIP | 15% |

> 쿠폰 할인은 정액(`AMOUNT`) 또는 정률(`PERCENT`) 중 하나로 적용한다.

---

## 4. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-01 | 백엔드/프론트엔드는 각각 단위 테스트를 보유한다. |
| NFR-02 | Docker 이미지로 빌드/배포 가능해야 한다. |
| NFR-03 | 환경 변수(`.env`)로 DB 접속/시크릿/CORS 설정을 주입한다. |
| NFR-04 | CI 파이프라인에서 lint/test/build가 자동 실행된다. |

---

## 5. 변경 영향도 데모 시나리오 매핑

본 프로젝트는 아래 변경 시나리오별 브랜치를 제공한다. 각 시나리오는 의도적으로 "영향 받는 다른 파일이 미반영된" 상태를 포함한다.

| 시나리오 브랜치 | 변경 트리거 | 영향 받는 영역 |
|-----------------|-------------|----------------|
| `scenario/req-change` | 요구사항서만 변경/추가 | 미구현 코드(요구사항↔구현 추적) |
| `scenario/db-schema-change` | DB 스키마(모델) 변경 | schema, router, frontend type, docs |
| `scenario/shared-component-change` | 프론트 공통 컴포넌트 수정 | 해당 컴포넌트를 쓰는 전 페이지 |
| `scenario/api-spec-change` | FastAPI API 스펙 변경 | frontend api client·hooks, 연관 백엔드 로직 |
| `scenario/env-var-change` | Docker 환경 변수 추가 | Dockerfile, docker-compose, config, CI |
| `scenario/discount-policy-change` | 백엔드 공통 서비스(할인) 변경 | order_service, 테스트, 프론트 표시 로직 |

각 시나리오의 상세 영향 분석은 [docs/scenarios.md](scenarios.md) 참고.
