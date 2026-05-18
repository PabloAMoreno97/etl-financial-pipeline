import pandas as pd
from src.transformations.metrics import compute_metrics


def test_compute_metrics_returns_expected_columns(sample_ohlcv):
    result = compute_metrics(sample_ohlcv)
    expected = {"symbol", "date", "close", "ma_7", "ma_21", "ma_50",
                "volatility_21", "daily_return", "cumulative_return"}
    assert set(result.columns) == expected


def test_compute_metrics_preserves_row_count(sample_ohlcv):
    result = compute_metrics(sample_ohlcv)
    assert len(result) == len(sample_ohlcv)


def test_ma_7_equals_rolling_mean(sample_ohlcv):
    result = compute_metrics(sample_ohlcv)
    expected_ma7 = sample_ohlcv.sort_values("date")["close"].rolling(7, min_periods=1).mean()
    pd.testing.assert_series_equal(
        result["ma_7"].reset_index(drop=True),
        expected_ma7.reset_index(drop=True),
        check_names=False,
    )


def test_daily_return_first_row_is_nan(sample_ohlcv):
    result = compute_metrics(sample_ohlcv)
    assert pd.isna(result.iloc[0]["daily_return"])


def test_cumulative_return_is_monotonically_consistent(sample_ohlcv):
    """With a strictly increasing close price, cumulative return should also be increasing."""
    result = compute_metrics(sample_ohlcv)
    cumret = result["cumulative_return"].dropna()
    assert (cumret.diff().dropna() >= 0).all()


def test_volatility_21_is_non_negative(sample_ohlcv):
    result = compute_metrics(sample_ohlcv)
    non_null = result["volatility_21"].dropna()
    assert (non_null >= 0).all()


def test_sorted_by_date_ascending(sample_ohlcv):
    shuffled = sample_ohlcv.sample(frac=1, random_state=42)
    result = compute_metrics(shuffled)
    assert list(result["date"]) == sorted(result["date"])
