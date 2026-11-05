from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    hash_scheme: Literal["argon2id"] = "argon2id"
    secret_key: str = Field(min_length=32)
    app_env: Literal["development", "production", "test"] = "development"
    port: int = Field(default=8000, ge=1, le=65535)
    argon2_time_cost: int = Field(default=3, ge=1, le=10)
    argon2_memory_cost: int = Field(default=65536, ge=8192, le=1048576)
    argon2_parallelism: int = Field(default=4, ge=1, le=16)
    token_ttl_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("Требуется PostgreSQL с драйвером psycopg")
        return value


settings = Settings()
