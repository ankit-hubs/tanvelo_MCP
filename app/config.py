"""
Tanvelo Configuration Settings
Production-grade configuration management with environment-based overrides.
"""

from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. Environment & Security
    TANVELO_ENV: str = "development"  # "development", "staging", "production", "testing"
    SECRET_KEY: str = "tv_sec_default_secret_key_please_change_in_production"
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024  # 2MB max payload

    # 2. Database & Connection Pooling
    DATABASE_URL: str = "sqlite+aiosqlite:///./tanvelo.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800  # 30 minutes
    DB_POOL_PRE_PING: bool = True

    # 3. LLM / Decision Engine Configuration
    LLM_PROVIDER: str = "nvidia"  # "nvidia", "openai", "anthropic", "ollama", "mock"
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "nemotron-mini"

    # 4. Embedding Configuration
    EMBEDDING_PROVIDER: str = "nvidia"  # "nvidia", "openai", "ollama", "mock"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_CACHE_SIZE: int = 5000

    # 5. Memory Decision & Hybrid Ranking Weights
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85
    RANKING_WEIGHT_SIMILARITY: float = 0.60
    RANKING_WEIGHT_IMPORTANCE: float = 0.25
    RANKING_WEIGHT_RECENCY: float = 0.15
    DEFAULT_TOP_K: int = 5
    RECENCY_HALF_LIFE_DAYS: float = 30.0

    # 6. Rate Limiting & Safety
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    HTTP_TIMEOUT_SECONDS: float = 10.0

    # 7. Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MCP_PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_production(self) -> bool:
        return self.TANVELO_ENV.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.TANVELO_ENV.lower() == "testing"


settings = Settings()
