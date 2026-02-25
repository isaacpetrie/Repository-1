"""Disk cache helpers for HAL."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


class CacheStore:
    """Simple disk cache for HTML/text/screenshots and metadata."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.html_dir = base_dir / "html"
        self.text_dir = base_dir / "text"
        self.shot_dir = base_dir / "screenshots"
        for d in (self.html_dir, self.text_dir, self.shot_dir):
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def cache_key(url: str, fetched_at: datetime, mode: str) -> str:
        day = fetched_at.strftime("%Y-%m-%d")
        raw = f"{url}|{day}|{mode}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:24]

    def html_path(self, key: str) -> Path:
        return self.html_dir / f"{key}.html"

    def text_path(self, key: str) -> Path:
        return self.text_dir / f"{key}.json"

    def screenshot_path(self, key: str, suffix: str = "full") -> Path:
        return self.shot_dir / f"{key}_{suffix}.png"

    def save_html(self, key: str, html: str) -> Path:
        path = self.html_path(key)
        path.write_text(html, encoding="utf-8")
        return path

    def save_text_json(self, key: str, payload: dict) -> Path:
        path = self.text_path(key)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
