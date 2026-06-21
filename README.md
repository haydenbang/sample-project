# ShopAdmin — 쇼핑몰 백오피스 샘플 프로젝트

`change-propagator` 앱의 **변경 영향도 분석 데모**를 위한 타깃 샘플 프로젝트입니다.
React(프론트엔드) + FastAPI(백엔드)로 구성된 SPA 백오피스로, 상품/주문/회원을 관리합니다.

## 구성

```
sample-project/
├── docs/                  # 요구사항서·DB스키마·API명세·시나리오 문서
├── backend/               # FastAPI + SQLAlchemy + pytest
│   ├── app/
│   │   ├── models/ schemas/ routers/ services/ common/
│   │   ├── config.py      # 환경 변수 주입 지점
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/              # Vite + React + TS + vitest
│   ├── src/
│   │   ├── components/common/  # StatusBadge·PageHeader·DataTable (공통)
│   │   ├── pages/ hooks/ types/ api/ utils/
│   │   └── __tests__/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── scripts/deploy.sh
└── ci/ci.yml             # 샘플 CI/CD 파이프라인 정의 (데모용, 실행되지는 않음)
```

## 문서

| 문서 | 설명 |
|------|------|
| [기능 요구사항서](docs/requirements.md) | 기능/비기능 요구사항 |
| [DB 스키마 정의서](docs/db-schema.md) | 테이블·컬럼·Enum 정의 |
| [API 명세서](docs/api-spec.md) | REST 엔드포인트 계약 |
| [변경 영향 시나리오](docs/scenarios.md) | 데모 브랜치별 영향 범위 |

## 로컬 실행

### 백엔드
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload          # http://localhost:8000/docs
pytest                                  # 단위 테스트
```

기본 계정: `admin@shopadmin.io / admin1234` (ADMIN), `user@shopadmin.io / user1234` (VIEWER)

### 프론트엔드
```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
npm run test                            # 단위 테스트
```

### Docker
```bash
docker compose up --build               # frontend :8080 / backend :8000
```

## 변경 영향도 데모 시나리오

각 시나리오는 별도 브랜치로 제공되며, `main` 과의 diff 로 영향 범위를 비교합니다.
자세한 내용은 [docs/scenarios.md](docs/scenarios.md) 참고.

| 브랜치 | 변경 트리거 | 영향 |
|--------|-------------|------|
| `scenario/req-change` | 요구사항서 신규 요구사항 추가 | 미구현 코드 추적 |
| `scenario/db-schema-change` | `users` 컬럼 추가 | model→schema→router→type→docs |
| `scenario/shared-component-change` | 공통 `StatusBadge` props 변경 | 사용하는 전 페이지 |
| `scenario/api-spec-change` | `/api/orders` 응답 필드 변경 | client→hooks→page, 백엔드 스키마 |
| `scenario/env-var-change` | 환경 변수 `PAYMENT_API_KEY` 추가 | config→Dockerfile→compose→CI |
| `scenario/discount-policy-change` | 할인 서비스 변경 | order_service→tests→프론트 표시 |
