"""Configuration helpers for HAL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_api_key: str | None
    cache_dir: Path
    allowlist_domains: list[str]
    browser_timeout_ms: int


def _parse_allowlist(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def get_settings() -> Settings:
    """Load settings from environment."""
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        cache_dir=Path(os.getenv("HAL_CACHE_DIR", ".hal_cache")),
        allowlist_domains=_parse_allowlist(os.getenv("HAL_ALLOWLIST_DOMAINS")),
        browser_timeout_ms=int(os.getenv("HAL_BROWSER_TIMEOUT_MS", "20000")),
    )
