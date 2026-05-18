from __future__ import annotations

import time
import logging
from datetime import date
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alphavantage.co/query"

# Free tier: 25 requests/day, 5 requests/minute
_REQUEST_DELAY = 12.0  # seconds between requests to stay under rate limit


class AlphaVantageClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._session = requests.Session()
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY - elapsed)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        params["apikey"] = self.api_key
        response = self._session.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        self._last_request_at = time.monotonic()
        data = response.json()
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            logger.warning("Alpha Vantage rate limit note: %s", data["Note"])
        return data

    def get_daily_prices(
        self,
        symbol: str,
        outputsize: str = "compact",
    ) -> list[dict[str, Any]]:
        """
        Fetch daily OHLCV prices for a symbol.
        outputsize: 'compact' (last 100 days) | 'full' (20+ years)
        """
        data = self._get({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        })
        time_series = data.get("Time Series (Daily)", {})
        rows = []
        for date_str, values in time_series.items():
            rows.append({
                "symbol": symbol.upper(),
                "date": date.fromisoformat(date_str),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            })
        logger.info("Fetched %d daily records for %s", len(rows), symbol)
        return rows
