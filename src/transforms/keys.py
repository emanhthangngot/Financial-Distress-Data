from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256


def stable_company_key(ticker: str) -> str:
    if ticker is None or not str(ticker).strip():
        raise ValueError("ticker is required for company_key")
    return sha256(str(ticker).strip().upper().encode("utf-8")).hexdigest()[:16]


def date_key(value: str | date | datetime) -> int:
    if isinstance(value, datetime):
        value = value.date()
    elif isinstance(value, str):
        value = datetime.fromisoformat(value[:10]).date()
    if not isinstance(value, date):
        raise ValueError("date_key requires a date, datetime, or ISO date string")
    return int(value.strftime("%Y%m%d"))
