# 쇼핑몰 백오피스 샘플 프로젝트

> change-propagator 데모용 샘플 코드베이스

## 개요

유통/쇼핑몰 백오피스 시스템의 샘플 구현체입니다.
Python FastAPI 백엔드와 React/TypeScript 프론트엔드로 구성되어 있으며,
**change-propagator** 도구가 Backend 구조 변화(DB/API/Domain)를 감지하고
Full-Stack 전체 영향을 자동 분석하는 시나리오 데모에 사용됩니다.

## 기술 스택

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL
- **Frontend**: React 18, TypeScript, Axios
- **Auth**: JWT (python-jose)

## 프로젝트 구조

```
sample-project/
├── docs/
│   ├── db-schema.md        ← DB 스키마 정의 (ERD)
│   ├── requirements.md     ← 기능 요구사항
│   └── api-spec.md         ← API 명세
├── backend/
│   ├── main.py             ← FastAPI 앱 엔트리포인트
│   ├── database.py         ← DB 연결 설정
│   ├── common/             ← 인증, 의존성
│   ├── models/             ← SQLAlchemy ORM 모델
│   ├── schemas/            ← Pydantic 스키마
│   ├── routers/            ← API 라우터
│   └── services/           ← 비즈니스 로직
└── frontend/src/
    ├── types/              ← TypeScript 타입 정의
    ├── hooks/              ← React Query 훅
    ├── components/         ← UI 컴포넌트
    └── pages/              ← 페이지 컴포넌트
```

## 시나리오 브랜치

| 브랜치 | 시나리오 |
|---|---|
| `scenario/1-db-schema-change` | 회원 등급 및 상태 관리 고도화 |
| `scenario/2-order-api-change` | 주문 API 배송 정보 구조 변경 |
| `scenario/3-auth-module-change` | 인증 모듈 권한 체계 강화 |
| `scenario/4-discount-policy-change` | 복합 할인 정책 도입 |

## 실행 방법

### Backend

```bash
cd backend
pip install fastapi uvicorn sqlalchemy pydantic[email] python-jose[cryptography] psycopg2-binary
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
