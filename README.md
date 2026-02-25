# HAL FastAPI Server

A small FastAPI service that fetches web pages and returns extracted content.

## Run

```bash
uvicorn hal.server:app --reload
```

## Endpoints

- `POST /browse` returns JSON (includes fields like `url`, `fetched_at`, `method_used`, `title`, `text_markdown`, `warnings`).
- `POST /browse_html` returns an HTML page rendering `text_markdown` (and optional `tables_markdown`) with metadata.

### Example: `/browse`

```bash
curl -X POST "http://127.0.0.1:8000/browse" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

### Example: `/browse_html`

```bash
curl -X POST "http://127.0.0.1:8000/browse_html" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

You can also use the interactive API docs at `http://127.0.0.1:8000/docs` to test `/browse_html` directly in a browser.
