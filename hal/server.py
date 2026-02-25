from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

import httpx
import markdown
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="HAL FastAPI Server")


class BrowseRequest(BaseModel):
    url: HttpUrl
    timeout_seconds: float = 15.0
    user_agent: str | None = None


def _extract_content(request: BrowseRequest) -> dict[str, Any]:
    warnings: list[str] = []
    headers: dict[str, str] = {}
    if request.user_agent:
        headers["User-Agent"] = request.user_agent

    try:
        response = httpx.get(str(request.url), timeout=request.timeout_seconds, headers=headers, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text_content = "\n\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())

    if not text_content:
        warnings.append("No readable text content found.")

    return {
        "url": str(response.url),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "method_used": "httpx",
        "status_code": response.status_code,
        "title": title,
        "text_markdown": text_content,
        "warnings": warnings,
    }


@app.post("/browse")
def browse(request: BrowseRequest) -> dict[str, Any]:
    return _extract_content(request)


def _markdown_to_safe_html(md_text: str) -> str:
    escaped_markdown = escape(md_text)
    return markdown.markdown(
        escaped_markdown,
        extensions=["extra", "sane_lists", "toc"],
        output_format="html5",
    )


@app.post("/browse_html", response_class=HTMLResponse)
def browse_html(request: BrowseRequest) -> HTMLResponse:
    result = _extract_content(request)

    title = result.get("title") or result.get("url") or "HAL Browse Result"
    warnings = result.get("warnings") or []
    warnings_html = ""
    if warnings:
        warnings_items = "".join(f"<li>{escape(warning)}</li>" for warning in warnings)
        warnings_html = (
            "<section class='callout warning'>"
            "<h2>Warnings</h2>"
            f"<ul>{warnings_items}</ul>"
            "</section>"
        )

    main_content_html = _markdown_to_safe_html(result.get("text_markdown") or "")

    tables_section_html = ""
    tables_markdown = result.get("tables_markdown")
    if tables_markdown:
        tables_html = _markdown_to_safe_html(str(tables_markdown))
        tables_section_html = (
            "<section>"
            "<h2>Tables</h2>"
            f"{tables_html}"
            "</section>"
        )

    html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escape(str(title))}</title>
    <style>
      :root {{ color-scheme: light dark; }}
      body {{
        margin: 0;
        padding: 2rem 1rem;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
      }}
      main {{ max-width: 860px; margin: 0 auto; }}
      header h1 {{ margin-bottom: 0.5rem; }}
      .meta {{ color: #666; font-size: 0.95rem; margin-bottom: 1.2rem; }}
      .meta a {{ word-break: break-all; }}
      .callout.warning {{
        border-left: 4px solid #eab308;
        background: rgba(234, 179, 8, 0.12);
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 1rem 0 1.5rem;
      }}
      pre, code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
      pre {{
        padding: 0.8rem;
        border-radius: 6px;
        overflow-x: auto;
        background: rgba(100, 116, 139, 0.14);
      }}
      table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
      th, td {{ border: 1px solid #cbd5e1; padding: 0.5rem; text-align: left; vertical-align: top; }}
      th {{ background: rgba(100, 116, 139, 0.15); }}
      blockquote {{ border-left: 3px solid #94a3b8; margin: 1rem 0; padding-left: 0.8rem; color: #475569; }}
      img {{ max-width: 100%; height: auto; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>{escape(str(title))}</h1>
        <div class=\"meta\">
          <div><strong>URL:</strong> <a href=\"{escape(str(result['url']))}\">{escape(str(result['url']))}</a></div>
          <div><strong>Fetched:</strong> {escape(str(result['fetched_at']))}</div>
          <div><strong>Method:</strong> {escape(str(result['method_used']))}</div>
        </div>
      </header>
      {warnings_html}
      <section>
        {main_content_html}
      </section>
      {tables_section_html}
    </main>
  </body>
</html>
"""

    return HTMLResponse(content=html)
