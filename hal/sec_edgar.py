from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

from hal.cache import sec_cache_dir, write_json

SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
ALLOWED_FORMS = {"10-K", "10-Q"}


class SecEdgarError(RuntimeError):
    """Raised for SEC integration failures."""


class SecClient:
    """Small SEC API client with rate limiting and retry/backoff."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 20.0,
        max_retries: int = 4,
        max_requests_per_second: int = 10,
    ) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/html;q=0.9, text/plain;q=0.8",
            },
        )
        self._max_retries = max_retries
        self._min_interval = 1.0 / max_requests_per_second
        self._last_request_ts = 0.0
        self._lock = Lock()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last_request_ts
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last_request_ts = time.monotonic()

    def get(self, url: str) -> httpx.Response:
        backoff = 0.5
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    raise SecEdgarError(f"SEC request failed for {url}: {exc}") from exc
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code in (429, 503):
                if attempt >= self._max_retries:
                    raise SecEdgarError(
                        f"SEC temporarily unavailable ({resp.status_code}) for {url}"
                    )
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(float(retry_after))
                else:
                    time.sleep(backoff)
                    backoff *= 2
                continue

            if resp.status_code >= 400:
                raise SecEdgarError(f"SEC request returned {resp.status_code} for {url}")
            return resp

        raise SecEdgarError(f"SEC request failed for {url}: {last_error}")


def _get_user_agent() -> str:
    user_agent = os.getenv("HAL_SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SecEdgarError(
            "HAL_SEC_USER_AGENT must be set (example: 'HAL/0.1 (you@example.com)')."
        )
    return user_agent


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _build_client() -> SecClient:
    return SecClient(user_agent=_get_user_agent())


def get_cik_for_ticker(ticker: str) -> str:
    """Resolve a ticker to zero-padded 10-digit CIK using SEC company_tickers.json."""
    normalized = _normalize_ticker(ticker)
    if not normalized:
        raise SecEdgarError("Ticker cannot be blank.")

    client = _build_client()
    try:
        response = client.get(f"{SEC_DATA_BASE}/files/company_tickers.json")
        payload = response.json()
    finally:
        client.close()

    for _, company in payload.items():
        if company.get("ticker", "").upper() == normalized:
            cik_num = str(company["cik_str"])
            return cik_num.zfill(10)
    raise SecEdgarError(f"Ticker '{normalized}' was not found in SEC ticker mapping.")


def get_recent_filings(cik: str) -> list[dict[str, str]]:
    """Fetch recent filings list from SEC submissions endpoint."""
    client = _build_client()
    try:
        url = f"{SEC_DATA_BASE}/submissions/CIK{cik}.json"
        response = client.get(url)
        payload = response.json()
    finally:
        client.close()

    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accepted_dates = recent.get("acceptanceDateTime", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    result: list[dict[str, str]] = []
    count = min(len(forms), len(filing_dates), len(accessions), len(primary_docs))
    for i in range(count):
        result.append(
            {
                "form": forms[i],
                "filingDate": filing_dates[i],
                "acceptedDate": accepted_dates[i] if i < len(accepted_dates) else "",
                "accessionNumber": accessions[i],
                "primaryDocument": primary_docs[i],
            }
        )
    return result


def _parse_dt(record: dict[str, str]) -> datetime:
    accepted = record.get("acceptedDate", "")
    filing_date = record.get("filingDate", "")
    if accepted:
        accepted_norm = accepted.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(accepted_norm)
        except ValueError:
            pass
    if filing_date:
        return datetime.fromisoformat(filing_date)
    return datetime.min


def choose_latest_10k_10q(filings: list[dict[str, str]]) -> dict[str, str]:
    """Select the newest filing among 10-K and 10-Q by acceptedDate/filingDate."""
    candidates = [f for f in filings if f.get("form") in ALLOWED_FORMS]
    if not candidates:
        raise SecEdgarError("No 10-K or 10-Q filings were found for this company.")
    return max(candidates, key=_parse_dt)


def _clean_accession(accession: str) -> str:
    return accession.replace("-", "")


def filing_document_url(cik: str, accession: str, primary_doc: str) -> str:
    clean_accession = _clean_accession(accession)
    cik_no_zero = str(int(cik))
    return f"{SEC_ARCHIVES_BASE}/{cik_no_zero}/{clean_accession}/{primary_doc}"


def download_filing(cik: str, accession: str, primary_doc: str, dest_dir: Path | None = None) -> dict[str, str]:
    """Download primary filing document into HAL cache and return stored file paths."""
    target_dir = dest_dir or sec_cache_dir(cik, accession)
    target_dir.mkdir(parents=True, exist_ok=True)

    url = filing_document_url(cik, accession, primary_doc)
    client = _build_client()
    try:
        resp = client.get(url)
        body = resp.text
    finally:
        client.close()

    file_path = target_dir / primary_doc
    file_path.write_text(body, encoding="utf-8", errors="ignore")

    metadata = {
        "cik": cik,
        "accession": accession,
        "primary_document": primary_doc,
        "sec_url": url,
        "downloaded_at": datetime.utcnow().isoformat() + "Z",
    }
    write_json(target_dir / "metadata.json", metadata)

    return {
        "download_path": str(file_path),
        "metadata_path": str(target_dir / "metadata.json"),
        "sec_url": url,
    }


def extract_text_from_filing_html(html: str) -> str:
    """Convert filing HTML to readable markdown-ish text with simple regex heuristics."""
    without_scripts = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    without_styles = re.sub(r"<style[\s\S]*?</style>", "", without_scripts, flags=re.IGNORECASE)
    with_breaks = re.sub(r"</?(p|div|br|tr|li|h[1-6])[^>]*>", "\n", without_styles, flags=re.IGNORECASE)
    stripped = re.sub(r"<[^>]+>", "", with_breaks)
    unescaped = (
        stripped.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#160;", " ")
    )
    normalized = re.sub(r"\r\n?", "\n", unescaped)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    return normalized.strip()


def get_latest_filing_bundle(
    ticker: str,
    *,
    include_exhibits: bool = False,
    output_format: str = "html",
    download: bool = True,
) -> dict[str, Any]:
    """High-level workflow for SEC latest 10-K/10-Q retrieval."""
    normalized_ticker = _normalize_ticker(ticker)
    cik = get_cik_for_ticker(normalized_ticker)
    filings = get_recent_filings(cik)
    selected = choose_latest_10k_10q(filings)

    accession = selected["accessionNumber"]
    primary_doc = selected["primaryDocument"]
    sec_url = filing_document_url(cik, accession, primary_doc)
    warnings: list[str] = []
    if include_exhibits:
        warnings.append("include_exhibits is not implemented yet; returning primary filing only.")

    html_content = ""
    download_path: str | None = None
    html_path: str | None = None

    if download:
        downloaded = download_filing(cik, accession, primary_doc)
        download_path = downloaded["download_path"]
        html_path = download_path if output_format == "html" else None
        html_content = Path(downloaded["download_path"]).read_text(encoding="utf-8", errors="ignore")
    else:
        client = _build_client()
        try:
            html_content = client.get(sec_url).text
        finally:
            client.close()

    text_markdown = extract_text_from_filing_html(html_content)

    response: dict[str, Any] = {
        "ticker": normalized_ticker,
        "cik": cik,
        "form_type": selected["form"],
        "filing_date": selected.get("filingDate", ""),
        "accession": accession,
        "primary_document": primary_doc,
        "sec_url": sec_url,
        "download_path": download_path,
        "text_markdown": text_markdown if output_format in {"text", "html"} else None,
        "html_path": html_path,
        "warnings": warnings,
        "citations": [{"type": "url", "value": sec_url}],
    }

    if output_format == "text":
        response["html_path"] = None

    return response
