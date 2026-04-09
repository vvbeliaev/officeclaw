from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    encryption_key: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("encryption_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        from cryptography.fernet import Fernet
        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError(f"ENCRYPTION_KEY is not a valid Fernet key: {exc}") from exc
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
