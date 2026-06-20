from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import users, orders, products
from routers import auth as auth_router

# 테이블 자동 생성 (개발 환경용)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="쇼핑몰 백오피스 API",
    description="쇼핑몰 백오피스 시스템 REST API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["인증"])
app.include_router(users.router, prefix="/api/v1/users", tags=["회원"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["주문"])
app.include_router(products.router, prefix="/api/v1/products", tags=["상품"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "backoffice-api"}
