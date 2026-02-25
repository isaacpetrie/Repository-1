"""Pydantic models for HAL API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ScreenshotOptions(BaseModel):
    full_page: bool = True
    selectors: list[str] = Field(default_factory=list)


class WaitOptions(BaseModel):
    timeout_ms: int = 20000
    network_idle: bool = True
    selector: str | None = None


class BrowseRequest(BaseModel):
    url: HttpUrl
    mode: Literal["auto", "dom", "vision"] = "auto"
    visual_extraction: bool = False
    screenshot: ScreenshotOptions = Field(default_factory=ScreenshotOptions)
    wait: WaitOptions = Field(default_factory=WaitOptions)


class Citation(BaseModel):
    type: Literal["url", "screenshot"]
    value: str


class BrowseResponse(BaseModel):
    url: str
    fetched_at: datetime
    method_used: Literal["dom", "vision"]
    title: str
    text_markdown: str
    tables_markdown: str | None = None
    links: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    citations: list[Citation] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
