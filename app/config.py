"""
Tanvelo Configuration Settings
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    TANVELO_ENV: str = "development"
    SECRET_KEY: str = "tv_sec_default_secret_key_please_change"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./tanvelo.db"

    # NVIDIA Nemotron Nano 8B Configuration
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "nvidia"  # "nvidia", "openai", or "mock"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    EMBEDDING_DIMENSION: int = 1536

    # Memory Decision & Ranking Weights
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85
    RANKING_WEIGHT_SIMILARITY: float = 0.60
    RANKING_WEIGHT_IMPORTANCE: float = 0.25
    RANKING_WEIGHT_RECENCY: float = 0.15
    DEFAULT_TOP_K: int = 5

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"


settings = Settings()
