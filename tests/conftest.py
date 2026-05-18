import pytest
import pandas as pd


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """30 trading days of synthetic OHLCV data for AAPL."""
    dates = pd.bdate_range(start="2024-01-01", periods=30)
    closes = [
        180.0, 182.5, 181.0, 183.2, 185.0,
        184.5, 186.0, 185.5, 187.0, 188.3,
        187.8, 189.0, 190.5, 191.0, 190.0,
        192.5, 193.0, 192.0, 194.0, 195.5,
        195.0, 196.5, 197.0, 196.0, 198.0,
        199.5, 200.0, 199.0, 201.0, 202.5,
    ]
    return pd.DataFrame({
        "symbol": ["AAPL"] * 30,
        "date": [d.date() for d in dates],
        "open": [c - 1.0 for c in closes],
        "high": [c + 2.0 for c in closes],
        "low": [c - 2.0 for c in closes],
        "close": closes,
        "volume": [50_000_000] * 30,
    })
