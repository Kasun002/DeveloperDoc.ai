import os

from dotenv import load_dotenv
from pydantic import BaseSettings

# Load environment variables from .env file if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "DeveloperDocAI"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = ""
    secret_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
