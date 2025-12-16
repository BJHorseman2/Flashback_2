"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/flashback"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Google Cloud
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gcs_bucket: str = "flashback-assets"

    # Vertex AI / Gemini
    gemini_model: str = "gemini-2.0-flash-exp"
    image_model: str = "imagen-3.0-generate-001"

    # Rate limits
    free_tier_weekly_limit: int = 5

    # Cache TTL
    cache_ttl_seconds: int = 86400  # 24 hours

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
