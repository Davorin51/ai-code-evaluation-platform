from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACE_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./evaluations.db"
    worker_url: str = "http://127.0.0.1:8001"
    worker_token: str = Field(default="local-development-only", min_length=16)
    request_timeout: float = Field(default=120, ge=5, le=300)
