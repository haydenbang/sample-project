#!/usr/bin/env bash
# ShopAdmin 배포 스크립트 (데모용)
# 이미지 빌드 -> 환경 변수 확인 -> docker-compose 기동
#
# 새 환경 변수를 추가하면 REQUIRED_ENV 목록과 Dockerfile/compose 에도 반영해야 한다.
# (변경 영향도 데모: scenario/env-var-change)

set -euo pipefail

# 배포에 필요한 (비밀) 환경 변수 목록
REQUIRED_ENV=("SECRET_KEY")

echo "==> 필수 환경 변수 확인"
for key in "${REQUIRED_ENV[@]}"; do
  if [ -z "${!key:-}" ]; then
    echo "오류: 환경 변수 ${key} 가 설정되지 않았습니다." >&2
    exit 1
  fi
done

echo "==> 이미지 빌드"
docker compose build

echo "==> 서비스 기동"
docker compose up -d

echo "==> 배포 완료. frontend: http://localhost:8080  backend: http://localhost:8000/api/health"
