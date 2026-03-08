from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://apex:apex_dev_2026@localhost:5432/apex_v2"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    ALGORITHM: str = "HS256"
    ANTHROPIC_API_KEY: str = ""

    # AI Model Configuration
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096

    # Cost rates per token (Claude Sonnet)
    COST_PER_INPUT_TOKEN: float = 0.000003
    COST_PER_OUTPUT_TOKEN: float = 0.000015

    # Confidence thresholds (Rule 5.4)
    AI_CONFIDENCE_THRESHOLD: float = 0.6       # Below this → pause for input
    AI_CONFIDENCE_AUTO_THRESHOLD: float = 0.8  # Above this → auto-complete in FULL_AUTO

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
