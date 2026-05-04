from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"
    project_name: str = "ChemIntel API"
    database_url: str = "postgresql+asyncpg://chemintel:chemintel@127.0.0.1:5433/chemintel"
    auto_create_schema: bool = False
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "chemintel-api"
    jwt_audience: str = "chemintel-api"
    jwt_expire_minutes: int = 120
    jwt_refresh_expire_days: int = 14
    default_tenant_id: str = "tenant_demo"
    demo_auth_enabled: bool = True
    allow_auto_user_signup: bool = True

    easyagent_path: str = str(Path(__file__).resolve().parents[3] / "EasyAgent")
    llm_provider: str = "openai"
    llm_model: str = "qwen3.5-9b"
    llm_base_url: str = "http://127.0.0.1:5124/v1"
    llm_api_key: str = "test"
    llm_enabled: bool = True
    llm_temperature: float = 0.1
    llm_timeout: int = 10

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = "http://127.0.0.1:5124/v1"
    embedding_api_key: str = "test"
    embedding_dimension: int = 384
    vector_search_enabled: bool = True

    rag_default_k: int = 4
    rag_multi_query_count: int = 3
    rag_initial_candidate_k: int = 8
    rag_profile: str = "balanced"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_runtime_settings(settings: Settings | None = None) -> None:
    current = settings or get_settings()
    if current.app_env.lower() not in {"prod", "production"}:
        return
    errors: list[str] = []
    if current.jwt_secret_key == "change-me":
        errors.append("JWT_SECRET_KEY must be changed in production")
    if current.jwt_algorithm == "HS256" and len(current.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters for HS256 production use")
    if current.demo_auth_enabled:
        errors.append("DEMO_AUTH_ENABLED must be false in production")
    if current.allow_auto_user_signup:
        errors.append("ALLOW_AUTO_USER_SIGNUP must be false in production")
    if current.allowed_origins == ["*"]:
        errors.append("ALLOWED_ORIGINS must be restricted in production")
    if errors:
        raise RuntimeError("Invalid production configuration: " + "; ".join(errors))
