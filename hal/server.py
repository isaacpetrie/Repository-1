"""FastAPI server for HAL browsing and extraction."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from hal.browser import fetch_with_playwright
from hal.cache import CacheStore
from hal.config import get_settings
from hal.extract_dom import extract_dom_content, should_use_vision
from hal.extract_vision import VisionExtractor
from hal.models import BrowseRequest, BrowseResponse, Citation, HealthResponse
from hal.safety import validate_url_safety

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("hal.server")

settings = get_settings()
cache = CacheStore(settings.cache_dir)
vision = VisionExtractor(settings.openai_api_key)

app = FastAPI(title="HAL")


@app.get("/", response_class=HTMLResponse)
async def ui() -> str:
    """Simple local GUI for browsing."""
    return """
<!doctype html><html><head><title>HAL GUI</title>
<style>body{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}textarea{width:100%;height:260px}</style>
</head><body>
<h1>HAL Local Agent Host</h1>
<p>Paste a URL and run extraction.</p>
<input id='url' style='width:80%' value='https://example.com'/>
<select id='mode'><option>auto</option><option>dom</option><option>vision</option></select>
<button onclick='run()'>Browse</button>
<pre id='meta'></pre>
<textarea id='out'></textarea>
<script>
async function run(){
  const url=document.getElementById('url').value;
  const mode=document.getElementById('mode').value;
  const res=await fetch('/browse',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({url,mode})});
  const data=await res.json();
  document.getElementById('meta').textContent=JSON.stringify({title:data.title,method:data.method_used,confidence:data.confidence,warnings:data.warnings},null,2);
  document.getElementById('out').value=data.text_markdown||JSON.stringify(data,null,2);
}
</script>
</body></html>
"""


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest) -> BrowseResponse:
    now = datetime.now(timezone.utc)
    url = str(req.url)
    try:
        validate_url_safety(url, settings.allowlist_domains)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = cache.cache_key(url, now, req.mode)
    warnings: list[str] = []
    try:
        fetch = await fetch_with_playwright(
            url=url,
            wait=req.wait,
            screenshot=req.screenshot,
            shot_path_fn=lambda suffix: cache.screenshot_path(key, suffix),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    cache.save_html(key, fetch.html)
    dom = extract_dom_content(fetch.html, fetch.title, fetch.body_text)
    warnings.extend(dom.warnings)

    use_vision = req.mode == "vision" or req.visual_extraction
    if req.mode == "auto" and should_use_vision(dom):
        use_vision = True
        warnings.append("Auto mode switched to vision due to extraction heuristics")

    if not use_vision or req.mode == "dom":
        resp = BrowseResponse(
            url=url,
            fetched_at=now,
            method_used="dom",
            title=dom.title,
            text_markdown=dom.text_markdown,
            tables_markdown=None,
            links=fetch.links,
            screenshots=fetch.screenshots,
            warnings=warnings,
            confidence=dom.confidence,
            citations=[Citation(type="url", value=url)],
        )
        cache.save_text_json(key, resp.model_dump(mode="json"))
        return resp

    if not vision.available():
        warnings.append("Vision requested but OPENAI_API_KEY not set; returned DOM extraction")
        resp = BrowseResponse(
            url=url,
            fetched_at=now,
            method_used="dom",
            title=dom.title,
            text_markdown=dom.text_markdown,
            tables_markdown=None,
            links=fetch.links,
            screenshots=fetch.screenshots,
            warnings=warnings,
            confidence=max(0.2, dom.confidence - 0.1),
            citations=[Citation(type="url", value=url)],
        )
        cache.save_text_json(key, resp.model_dump(mode="json"))
        return resp

    try:
        vr = vision.extract(fetch.screenshots)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Vision extraction failed: {exc}")
        resp = BrowseResponse(
            url=url,
            fetched_at=now,
            method_used="dom",
            title=dom.title,
            text_markdown=dom.text_markdown,
            tables_markdown=None,
            links=fetch.links,
            screenshots=fetch.screenshots,
            warnings=warnings,
            confidence=max(0.2, dom.confidence - 0.2),
            citations=[Citation(type="url", value=url)],
        )
        cache.save_text_json(key, resp.model_dump(mode="json"))
        return resp

    resp = BrowseResponse(
        url=url,
        fetched_at=now,
        method_used="vision",
        title=dom.title,
        text_markdown=vr.get("text_markdown", ""),
        tables_markdown=vr.get("tables_markdown"),
        links=fetch.links,
        screenshots=fetch.screenshots,
        warnings=warnings + vr.get("warnings", []),
        confidence=float(vr.get("confidence", 0.5)),
        citations=[Citation(type="url", value=url)]
        + [Citation(type="screenshot", value=p) for p in fetch.screenshots],
    )
    cache.save_text_json(key, resp.model_dump(mode="json"))
    return resp
