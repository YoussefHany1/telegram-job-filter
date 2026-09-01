"""
config.py

Loads and validates all runtime configuration from environment variables (.env).
No other module should read os.environ directly for app settings - they should
import the `settings` instance from here instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root as early as possible.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def _get_int(name: str) -> int:
    raw = os.getenv(name)
    if not raw:
        raise ConfigError(f"Missing required environment variable: {name}")
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer, got: {raw!r}") from exc


def _get_str(name: str, required: bool = True, default: str = "") -> str:
    raw = os.getenv(name, default)
    if required and not raw:
        raise ConfigError(f"Missing required environment variable: {name}")
    return raw


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    phone: str
    session_name: str
    string_session: str
    db_path: str
    log_level: str

    # By default, forward matches to Saved Messages ("me").
    # Configurable via FORWARD_DESTINATION in .env so you can use a private channel/group for notifications.
    destination: str

def load_settings() -> Settings:
    settings = Settings(
        api_id=_get_int("API_ID"),
        api_hash=_get_str("API_HASH"),
        phone=_get_str("PHONE"),
        session_name=_get_str("SESSION_NAME", required=False, default="job_filter_session"),
        string_session=_get_str("STRING_SESSION", required=False, default=""),
        db_path=_get_str("DB_PATH", required=False, default="data/job_filter.db"),
        log_level=_get_str("LOG_LEVEL", required=False, default="INFO"),
        destination=_get_str("FORWARD_DESTINATION", required=False, default="me"),
    )
    # Make sure the directory for the DB / session exists.
    Path(settings.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
    return settings


settings = load_settings()
