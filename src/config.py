"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables with validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Insurance Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT: int = 60
    OPENAI_MAX_RETRIES: int = 3

    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql://insurance:password@localhost:5432/insurance_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False  # Log all SQL queries (use in development only)

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SECONDS: int = 3600  # 1 hour
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_MAX_CONNECTIONS: int = 10

    # ChromaDB / Vector Store
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "insurance_FAQ_collection"
    CHROMA_EMBEDDING_FUNCTION: str = "default"  # Use Chroma's default
    FAQ_RETRIEVAL_TOP_K: int = 3

    # Phoenix Tracing (Optional)
    PHOENIX_ENABLED: bool = True
    PHOENIX_COLLECTOR_ENDPOINT: Optional[str] = "http://localhost:6006/v1/traces"
    PHOENIX_PROJECT_NAME: str = "multi-agent-system-prod"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    API_RELOAD: bool = False  # Hot reload for development

    # CORS
    CORS_ENABLED: bool = True
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # json or text

    # Agent Configuration
    SUPERVISOR_MAX_ITERATIONS: int = 3
    AGENT_TIMEOUT: int = 30  # seconds

    # Rate Limiting (optional, for future use)
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures we only load settings once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
