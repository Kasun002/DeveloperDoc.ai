"""
Application configuration management.

This module defines the Settings class that loads configuration from environment
variables using pydantic-settings. Configuration values are loaded from .env or
.env.local files if present, with sensible defaults for development.
"""

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env.local (local development) or .env file
# Priority: .env.local > .env > environment variables
env_local_path = os.path.join(os.path.dirname(__file__), "../../.env.local")
env_path = os.path.join(os.path.dirname(__file__), "../../.env")

if os.path.exists(env_local_path):
    load_dotenv(dotenv_path=env_local_path, override=True)
    print(f"✓ Loaded configuration from .env.local")
elif os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Loaded configuration from .env")
else:
    print("⚠ No .env or .env.local file found, using environment variables or defaults")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by environment variables. For example,
    DATABASE_URL environment variable will override the database_url field.

    Security considerations:
    - JWT_SECRET_KEY should be a strong random string (minimum 256 bits)
    - DATABASE_URL should not be committed to version control
    - Use different secrets for development and production
    """

    # Application settings
    app_env: str = "development"  # Environment: development, staging, production
    app_name: str = "DeveloperDocAI"  # Application name
    app_host: str = "0.0.0.0"  # Host to bind to
    app_port: int = 8000  # Port to listen on

    # Database configuration
    # Format: postgresql://user:password@host:port/database
    database_url: str = ""

    # JWT configuration
    jwt_secret_key: str = ""  # Secret key for signing JWT tokens (REQUIRED)
    jwt_algorithm: str = "HS256"  # Algorithm for JWT signing (HS256 or RS256)
    access_token_expire_minutes: int = 30  # Access token lifetime (30 minutes)
    refresh_token_expire_days: int = 7  # Refresh token lifetime (7 days)

    # Password reset configuration
    password_reset_token_expire_hours: int = 1  # Reset token lifetime (1 hour)

    # Password hashing configuration
    # Higher rounds = more secure but slower. 12 is a good balance.
    bcrypt_rounds: int = 12  # Number of bcrypt rounds (computational cost)

    # Other API keys
    secret_key: str = ""  # General purpose secret key
    openai_api_key: str = ""  # OpenAI API key for AI features

    class Config:
        """Pydantic configuration for Settings class."""

        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
# Import this instance throughout the application to access configuration
settings = Settings()
