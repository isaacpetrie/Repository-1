"""Playwright browser operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Browser, Error as PlaywrightError, Page, async_playwright

from hal.models import ScreenshotOptions, WaitOptions

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BrowserFetchResult:
    title: str
    html: str
    body_text: str
    links: list[str]
    screenshots: list[str]


async def _wait_for_page(page: Page, wait: WaitOptions) -> None:
    if wait.network_idle:
        await page.wait_for_load_state("networkidle", timeout=wait.timeout_ms)
    else:
        await page.wait_for_load_state("domcontentloaded", timeout=wait.timeout_ms)
    if wait.selector:
        await page.wait_for_selector(wait.selector, timeout=wait.timeout_ms)


async def _take_screenshots(page: Page, screenshot: ScreenshotOptions, shot_path_fn) -> list[str]:
    paths: list[str] = []
    full_path = shot_path_fn("full")
    await page.screenshot(path=str(full_path), full_page=screenshot.full_page)
    paths.append(str(full_path))

    for idx, selector in enumerate(screenshot.selectors):
        elem = await page.query_selector(selector)
        if not elem:
            continue
        path = shot_path_fn(f"selector_{idx}")
        await elem.screenshot(path=str(path))
        paths.append(str(path))
    return paths


async def fetch_with_playwright(
    url: str,
    wait: WaitOptions,
    screenshot: ScreenshotOptions,
    shot_path_fn,
) -> BrowserFetchResult:
    """Fetch rendered page data and screenshots via Chromium."""
    browser: Browser | None = None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=wait.timeout_ms, wait_until="domcontentloaded")
            await _wait_for_page(page, wait)
            title = await page.title()
            html = await page.content()
            body_text = await page.evaluate("document.body ? document.body.innerText : ''")
            links = await page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.href).filter(Boolean).slice(0, 200)"
            )
            screenshots = await _take_screenshots(page, screenshot, shot_path_fn)
            return BrowserFetchResult(title=title, html=html, body_text=body_text, links=links, screenshots=screenshots)
    except PlaywrightError as exc:
        logger.exception("Playwright failure for %s", url)
        raise RuntimeError(f"Browser error: {exc}") from exc
    finally:
        if browser is not None:
            await browser.close()
