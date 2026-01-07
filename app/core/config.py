from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Values can be overridden by creating a .env file in the project root.
    """

    # Project Info
    PROJECT_NAME: str = "Tasks API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A FastAPI application for managing tasks"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS - Origins allowed to access the API
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    # Security (for future authentication)
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str

    # Task Settings
    MAX_TASKS_PER_USER: int = 100
    DEFAULT_TASK_STATUS: str = "pending"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


# Create a singleton instance
settings = Settings()
