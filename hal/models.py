from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LatestFilingRequest(BaseModel):
    ticker: str = Field(..., min_length=1, description="Public company ticker symbol")
    include_exhibits: bool = Field(
        default=False,
        description="Reserved for future support; currently ignored for primary filing retrieval.",
    )
    format: Literal["html", "text"] = Field(default="html")
    download: bool = Field(default=True)


class Citation(BaseModel):
    type: Literal["url"]
    value: str


class LatestFilingResponse(BaseModel):
    ticker: str
    cik: str
    form_type: Literal["10-K", "10-Q"]
    filing_date: str
    accession: str
    primary_document: str
    sec_url: str
    download_path: str | None = None
    text_markdown: str | None = None
    html_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
