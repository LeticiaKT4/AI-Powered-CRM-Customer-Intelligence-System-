"""Application configuration from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/src/config.py -> crm-project/
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    crm_data_mode: str = "huggingface"  # mock | huggingface (CRMArena) | salesforce
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


def repo_root() -> Path:
    return _REPO_ROOT
