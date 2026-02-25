from __future__ import annotations

from fastapi import FastAPI, HTTPException

from hal.models import LatestFilingRequest, LatestFilingResponse
from hal.sec_edgar import SecEdgarError, get_latest_filing_bundle

app = FastAPI(title="HAL", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sec/latest_filing", response_model=LatestFilingResponse)
def latest_filing(payload: LatestFilingRequest) -> LatestFilingResponse:
    try:
        result = get_latest_filing_bundle(
            payload.ticker,
            include_exhibits=payload.include_exhibits,
            output_format=payload.format,
            download=payload.download,
        )
    except SecEdgarError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LatestFilingResponse(**result)
