# backend/app/core/config.py
"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "beacon-observatory"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/beacon.db"
    database_echo: bool = False

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    # Security (OIDC - future)
    oidc_enabled: bool = False
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None

    # LLM (future)
    llm_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None

    # Demo mode (local only)
    demo_mode: bool = True
    demo_mode_bind_address: str = "127.0.0.1"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()