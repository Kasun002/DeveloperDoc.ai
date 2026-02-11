"""
Application configuration management.

This module defines the Settings class that loads configuration from environment
variables using pydantic-settings. Configuration values are loaded from .env or
.env.local files if present, with sensible defaults for development.
"""

import os

from dotenv import load_dotenv
from pydantic import field_validator, ValidationError
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
    
    # Vector database configuration (for AI Agent pgvector operations)
    vector_database_url: str = ""

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
    
    # LLM Provider Configuration
    llm_provider: str = "openai"  # "openai" or "gemini"
    gemini_api_key: str = ""  # Only required if llm_provider="gemini"
    
    # Redis Configuration (for caching)
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # AI Agent Configuration
    semantic_cache_threshold: float = 0.95  # Similarity threshold (0.0-1.0)
    semantic_cache_ttl: int = 3600  # 1 hour in seconds
    tool_cache_ttl: int = 300  # 5 minutes in seconds
    
    # LangGraph workflow configuration
    max_workflow_iterations: int = 3
    
    # Vector search configuration
    vector_search_top_k: int = 10
    vector_search_min_score: float = 0.7
    
    # Cross-encoder model for re-ranking
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Embedding model
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # MCP Tool Configuration
    mcp_service_url: str = "http://localhost:8001"  # MCP service base URL
    mcp_tool_retry_attempts: int = 3
    mcp_tool_retry_backoff_multiplier: int = 1
    mcp_tool_retry_min_wait: int = 1
    mcp_tool_retry_max_wait: int = 10
    
    # Observability
    otel_enabled: bool = True
    otel_service_name: str = "ai-agent-system"
    otel_exporter_type: str = "console"  # console, jaeger, or otlp
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that database_url is provided and properly formatted."""
        if not v:
            raise ValueError("DATABASE_URL is required. Please set it in your .env file.")
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with 'postgresql://'")
        return v

    @field_validator("vector_database_url")
    @classmethod
    def validate_vector_database_url(cls, v: str) -> str:
        """Validate that vector_database_url is provided and properly formatted."""
        if not v:
            raise ValueError("VECTOR_DATABASE_URL is required. Please set it in your .env file.")
        if not v.startswith("postgresql://"):
            raise ValueError("VECTOR_DATABASE_URL must start with 'postgresql://'")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate that JWT secret key is provided and sufficiently strong."""
        if not v:
            raise ValueError("JWT_SECRET_KEY is required. Generate one with: openssl rand -hex 32")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long for security")
        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: str, info) -> str:
        """Validate that OpenAI API key is provided if using OpenAI"""
        llm_provider = info.data.get("llm_provider", "openai")
        if llm_provider == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return v

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, v: str, info) -> str:
        """Validate that Gemini API key is provided if using Gemini"""
        llm_provider = info.data.get("llm_provider", "openai")
        if llm_provider == "gemini" and not v:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        return v

    @field_validator("semantic_cache_threshold")
    @classmethod
    def validate_semantic_cache_threshold(cls, v: float) -> float:
        """Validate that semantic cache threshold is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("SEMANTIC_CACHE_THRESHOLD must be between 0.0 and 1.0")
        return v

    @field_validator("vector_search_min_score")
    @classmethod
    def validate_vector_search_min_score(cls, v: float) -> float:
        """Validate that vector search min score is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("VECTOR_SEARCH_MIN_SCORE must be between 0.0 and 1.0")
        return v

    class Config:
        """Pydantic configuration for Settings class."""

        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
# Import this instance throughout the application to access configuration
settings = Settings()


def validate_settings() -> None:
    """
    Validate all required settings are properly configured.
    
    This function should be called at application startup to ensure
    all required configuration is present before the application starts.
    
    Raises:
        ValueError: If any required configuration is missing or invalid
    """
    try:
        # Attempt to access settings to trigger validation
        _ = settings.database_url
        _ = settings.vector_database_url
        _ = settings.jwt_secret_key
        
        # Validate LLM provider specific keys
        if settings.llm_provider == "openai":
            _ = settings.openai_api_key
        elif settings.llm_provider == "gemini":
            _ = settings.gemini_api_key
        
        print("✓ All required configuration validated successfully")
    except ValidationError as e:
        print("✗ Configuration validation failed:")
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            print(f"  - {field}: {message}")
        raise ValueError("Configuration validation failed. Please check your .env file.") from e
