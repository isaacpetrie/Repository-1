from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CACHE_ROOT = Path(".hal_cache")


def sec_cache_dir(cik: str, accession: str) -> Path:
    """Return SEC cache path for a filing and create it if needed."""
    path = CACHE_ROOT / "sec" / cik / accession
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
