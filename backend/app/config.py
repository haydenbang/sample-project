"""애플리케이션 설정.

모든 배포 환경 변수는 이 모듈을 통해 주입된다.
새 환경 변수를 추가하면 Dockerfile / docker-compose.yml / CI / .env.example 에도
반영되어야 한다. (변경 영향도 데모: scenario/env-var-change)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 애플리케이션
    app_name: str = "ShopAdmin API"
    environment: str = "development"
    debug: bool = True

    # 데이터베이스
    database_url: str = "sqlite:///./shopadmin.db"

    # 보안 / JWT
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60

    # CORS (콤마 구분)
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
