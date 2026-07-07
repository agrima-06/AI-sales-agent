import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core settings
    ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Enterprise AI Sales Agent API"
    API_V1_STR: str = "/api/v1"
    
    # Correlation headers
    X_CORRELATION_ID_HEADER: str = "x-correlation-id"
    
    # Databases
    DATABASE_URL: str = "postgresql://postgres:postgres_secure_pass@db:5432/ai_sales_agent_dev"
    REDIS_URL: str = "redis://redis:6379/0"

    # AI & Integrations placeholders
    OPENAI_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(
        # Read from environment variables, and fallback to parent directory .env
        env_file=os.path.join(os.path.dirname(__file__), "../../../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
