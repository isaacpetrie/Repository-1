from __future__ import annotations

import pytest

from hal import sec_edgar
from hal.sec_edgar import SecEdgarError


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [("aapl", "AAPL"), ("  msft  ", "MSFT"), ("GoOg", "GOOG")],
)
def test_ticker_normalization(ticker: str, expected: str) -> None:
    assert sec_edgar._normalize_ticker(ticker) == expected


def test_choose_latest_10k_10q() -> None:
    filings = [
        {
            "form": "8-K",
            "filingDate": "2024-01-01",
            "acceptedDate": "2024-01-01T10:00:00-05:00",
            "accessionNumber": "a",
            "primaryDocument": "x.htm",
        },
        {
            "form": "10-K",
            "filingDate": "2024-02-10",
            "acceptedDate": "2024-02-10T08:00:00-05:00",
            "accessionNumber": "b",
            "primaryDocument": "k.htm",
        },
        {
            "form": "10-Q",
            "filingDate": "2024-05-01",
            "acceptedDate": "2024-05-01T06:00:00-05:00",
            "accessionNumber": "c",
            "primaryDocument": "q.htm",
        },
    ]

    selected = sec_edgar.choose_latest_10k_10q(filings)
    assert selected["form"] == "10-Q"
    assert selected["accessionNumber"] == "c"


def test_error_when_user_agent_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HAL_SEC_USER_AGENT", raising=False)

    with pytest.raises(SecEdgarError, match="HAL_SEC_USER_AGENT must be set"):
        sec_edgar._get_user_agent()
