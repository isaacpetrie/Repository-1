# HAL

HAL exposes API endpoints for retrieving SEC EDGAR filings.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .[dev]
```

## SEC latest filing endpoint

SEC requires a descriptive user-agent. Set this before running HAL:

```bash
export HAL_SEC_USER_AGENT="HAL/0.1 (your_email@example.com)"
# Windows PowerShell:
# $env:HAL_SEC_USER_AGENT = "HAL/0.1 (your_email@example.com)"
```

Run the API:

```bash
uvicorn hal.server:app --reload
```

Request the latest 10-K/10-Q filing for a ticker:

```bash
curl -X POST "http://127.0.0.1:8000/sec/latest_filing" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","include_exhibits":false,"format":"html","download":true}'
```

Sample response:

```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "form_type": "10-Q",
  "filing_date": "2025-02-01",
  "accession": "0000320193-25-000010",
  "primary_document": "a10q.htm",
  "sec_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000010/a10q.htm",
  "download_path": ".hal_cache/sec/0000320193/0000320193-25-000010/a10q.htm",
  "text_markdown": "...extracted filing text...",
  "html_path": ".hal_cache/sec/0000320193/0000320193-25-000010/a10q.htm",
  "warnings": [],
  "citations": [
    {
      "type": "url",
      "value": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000010/a10q.htm"
    }
  ]
}
```

Downloaded files are stored at:

```text
.hal_cache/sec/<cik>/<accession>/<filename>
```

with metadata saved as `metadata.json` in the same folder.
