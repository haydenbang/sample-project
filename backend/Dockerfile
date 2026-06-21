# ShopAdmin 백엔드 이미지
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# --- 배포 환경 변수 ---
# 새 환경 변수를 추가하면 이 ENV 목록과 docker-compose.yml, CI 에도 반영해야 한다.
# (변경 영향도 데모: scenario/env-var-change)
ENV ENVIRONMENT=production \
    DATABASE_URL=sqlite:///./shopadmin.db \
    SECRET_KEY=change-me-in-prod \
    ACCESS_TOKEN_EXPIRE_MINUTES=60 \
    CORS_ORIGINS=http://localhost

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
