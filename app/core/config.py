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
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    jwt_secret_key: str = "change-me"
    jwt_expire_minutes: int = 120
    default_tenant_id: str = "tenant_demo"

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

    rag_default_k: int = 4
    rag_multi_query_count: int = 3
    rag_initial_candidate_k: int = 8
    rag_profile: str = "balanced"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
