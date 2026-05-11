from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
from pathlib import Path


# Vault secrets file path (injected by Vault Agent Sidecar)
VAULT_SECRETS_PATH = Path("/vault/secrets")


def read_vault_secret(secret_name: str) -> Optional[str]:
    """
    Read a secret from Vault-injected file.
    Vault Agent Sidecar writes secrets to /vault/secrets/<secret_name>
    """
    secret_file = VAULT_SECRETS_PATH / secret_name
    if secret_file.exists():
        return secret_file.read_text().strip()
    return None


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or Vault secrets.

    Priority order:
    1. Vault-injected files (/vault/secrets/*)
    2. Environment variables
    3. .env file
    4. Default values
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

    # Security - loaded from Vault in production
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database - loaded from Vault in production
    DATABASE_URL: str = ""

    # Task Settings
    MAX_TASKS_PER_USER: int = 100
    DEFAULT_TASK_STATUS: str = "pending"

    # Vault Configuration
    VAULT_ENABLED: bool = False  # Set to True in production with Vault

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def load_secret_key(cls, v: str) -> str:
        """Load SECRET_KEY from Vault file if available, otherwise use env var."""
        vault_secret = read_vault_secret("secret_key")
        if vault_secret:
            return vault_secret
        if v:
            return v
        raise ValueError("SECRET_KEY must be set via Vault or environment variable")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def load_database_url(cls, v: str) -> str:
        """Load DATABASE_URL from Vault file if available, otherwise use env var."""
        vault_secret = read_vault_secret("database_url")
        if vault_secret:
            return vault_secret
        if v:
            return v
        raise ValueError("DATABASE_URL must be set via Vault or environment variable")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Create a singleton instance
settings = Settings()
