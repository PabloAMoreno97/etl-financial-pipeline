from __future__ import annotations

import pandas as pd


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Receives a DataFrame with columns [symbol, date, open, high, low, close, volume]
    sorted ascending by date. Returns a new DataFrame with computed analytics metrics.
    """
    df = df.sort_values("date").copy()

    df["daily_return"] = df["close"].pct_change()
    df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1

    df["ma_7"] = df["close"].rolling(window=7, min_periods=1).mean()
    df["ma_21"] = df["close"].rolling(window=21, min_periods=1).mean()
    df["ma_50"] = df["close"].rolling(window=50, min_periods=1).mean()

    # Annualized volatility (std of daily returns over 21-day window × √252)
    df["volatility_21"] = df["daily_return"].rolling(window=21, min_periods=2).std() * (252 ** 0.5)

    return df[[
        "symbol", "date", "close",
        "ma_7", "ma_21", "ma_50",
        "volatility_21", "daily_return", "cumulative_return",
    ]]
