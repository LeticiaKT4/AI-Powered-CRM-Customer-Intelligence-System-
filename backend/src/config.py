"""Application configuration from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    crm_data_mode: str = "mock"  # mock | huggingface | salesforce
    cache_ttl_seconds: int = 60
    analysis_timeout_seconds: int = 10
    max_page_size: int = 500

    sf_username: str = ""
    sf_password: str = ""
    sf_security_token: str = ""
    sf_domain: str = "login"


@lru_cache
def get_settings() -> Settings:
    return Settings()
