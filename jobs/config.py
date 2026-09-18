"""Reads settings from environment variables (and the local .env file, if present)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

VALID_ENVS = {"local", "ci", "production"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(Exception):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    database_url: str
    openai_api_key: str
    price_history_years: int


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Build Settings from `env` (defaults to the real environment plus .env)."""
    if env is None:
        load_dotenv()
        env = dict(os.environ)

    app_env = env.get("APP_ENV", "local").strip().lower()
    if app_env not in VALID_ENVS:
        raise ConfigError(f"APP_ENV must be one of {sorted(VALID_ENVS)}, got '{app_env}'")

    log_level = env.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}, got '{log_level}'")

    years_text = env.get("PRICE_HISTORY_YEARS", "3").strip()
    if not years_text.isdigit() or not 1 <= int(years_text) <= 20:
        raise ConfigError(
            f"PRICE_HISTORY_YEARS must be a whole number from 1 to 20, got '{years_text}'"
        )

    return Settings(
        app_env=app_env,
        log_level=log_level,
        database_url=env.get("DATABASE_URL", "").strip(),
        openai_api_key=env.get("OPENAI_API_KEY", "").strip(),
        price_history_years=int(years_text),
    )


def require(value: str, name: str) -> str:
    """Return `value`, or stop with a clear message if it is empty."""
    if not value:
        raise ConfigError(f"{name} is not set. Add it to your .env file (see .env.example).")
    return value
