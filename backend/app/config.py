from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    LLM_SERVICE_URL: str = "http://recruitment_llm:8001"
    # Paths
    UPLOAD_DIR: str = "./uploads"
    LOG_DIR: str = "./logs"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"  

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra='ignore'
    )


settings = Settings()
