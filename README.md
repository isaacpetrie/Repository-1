# HAL (Local-first AI Agent Host)

HAL is a local-first Python service + CLI that browses the web with Playwright, extracts main page text via DOM/Readability, and falls back to screenshot + vision extraction when needed.

## Features

- **FastAPI server** with:
  - `GET /health`
  - `POST /browse`
  - built-in local GUI at `GET /`
- **CLI**: `hal browse <url> [--mode auto|dom|vision] [--json] [--out <dir>]`
- **Extraction ladder**:
  1. DOM-based extraction (Readability + rendered body text fallback)
  2. Vision extraction via OpenAI Responses API if low confidence/short content/hints, or `mode=vision`
- **SSRF safety**: blocks localhost/private/link-local/metadata IPs, supports allowlist mode via `HAL_ALLOWLIST_DOMAINS`
- **Disk cache** in `.hal_cache/{html,text,screenshots}` keyed by URL + day + mode hash
- **Structured JSON output** per URL

## Requirements

- Python 3.11+
- Playwright Chromium browser binaries
- `OPENAI_API_KEY` (only needed for vision mode)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

### Linux troubleshooting (Playwright dependencies)

If Chromium fails to launch, run:

```bash
playwright install-deps chromium
```

For minimal distros, install common packages like `libnss3`, `libatk1.0-0`, `libx11-xcb1`, `libgtk-3-0`, `libdrm2`, `libgbm1`.

## Run server

```bash
uvicorn hal.server:app --reload
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- GUI: `http://127.0.0.1:8000/`

## Run CLI

```bash
hal browse https://example.com
hal browse https://example.com --mode auto --json
hal browse https://example.com --out outdir --json
```

## API request example

```bash
curl -X POST http://127.0.0.1:8000/browse \
  -H 'content-type: application/json' \
  -d '{
    "url": "https://example.com",
    "mode": "auto",
    "screenshot": {"full_page": true, "selectors": []},
    "wait": {"timeout_ms": 20000, "network_idle": true, "selector": null}
  }'
```

## Environment variables

- `OPENAI_API_KEY`: enables vision extraction
- `HAL_ALLOWLIST_DOMAINS`: comma-separated domain allowlist, e.g. `sec.gov,example.com`
- `HAL_CACHE_DIR`: cache directory path (default `.hal_cache`)
- `HAL_BROWSER_TIMEOUT_MS`: default timeout (default `20000`)

## Output schema

Each browse call returns:

```json
{
  "url": "https://...",
  "fetched_at": "2026-01-01T00:00:00Z",
  "method_used": "dom",
  "title": "...",
  "text_markdown": "...",
  "tables_markdown": "...",
  "links": ["..."],
  "screenshots": [".hal_cache/screenshots/...png"],
  "warnings": [],
  "confidence": 0.0,
  "citations": [{"type":"url","value":"https://..."}]
}
```

## Testing

```bash
pytest -q
```
