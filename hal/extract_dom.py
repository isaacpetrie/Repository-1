"""DOM-first extraction logic with readability fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # noqa: BLE001
    BeautifulSoup = None

try:
    from readability import Document  # type: ignore
except Exception:  # noqa: BLE001
    Document = None

PAYWALL_HINTS = ("enable javascript", "captcha", "subscribe to read", "paywall", "access denied")


@dataclass(slots=True)
class DomExtractionResult:
    title: str
    text_markdown: str
    warnings: list[str]
    confidence: float


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _html_to_text(html: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        return _clean_text(soup.get_text("\n"))
    return _clean_text(html)


def extract_dom_content(html: str, page_title: str, body_text: str) -> DomExtractionResult:
    """Extract primary text content from rendered HTML."""
    warnings: list[str] = []

    readable_title = page_title
    summary_text = ""

    if Document:
        doc = Document(html)
        readable_title = doc.short_title() or page_title
        summary_html = doc.summary(html_partial=True)
        summary_text = _html_to_text(summary_html)

    if len(summary_text) < 300:
        warnings.append("Readability returned short content, used body text fallback")
        summary_text = _clean_text(body_text)

    text_len = len(summary_text)
    lower = summary_text.lower()
    contains_hint = any(h in lower for h in PAYWALL_HINTS)
    lines = [ln for ln in summary_text.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln.strip()) < 40)
    nav_ratio = short_lines / max(len(lines), 1)

    confidence = 0.9
    if text_len < 800:
        confidence -= 0.35
    if contains_hint:
        confidence -= 0.25
    if nav_ratio > 0.7:
        confidence -= 0.2
    confidence = max(0.0, min(1.0, confidence))

    if contains_hint:
        warnings.append("Potential bot/captcha/paywall content detected")
    if nav_ratio > 0.7:
        warnings.append("High navigation boilerplate ratio detected")

    return DomExtractionResult(
        title=readable_title,
        text_markdown=summary_text,
        warnings=warnings,
        confidence=confidence,
    )


def should_use_vision(dom: DomExtractionResult) -> bool:
    """Decide if the extraction ladder should switch to vision."""
    text = dom.text_markdown.lower()
    too_short = len(dom.text_markdown) < 800
    hint = any(h in text for h in PAYWALL_HINTS)
    low_conf = dom.confidence < 0.55
    return too_short or hint or low_conf
