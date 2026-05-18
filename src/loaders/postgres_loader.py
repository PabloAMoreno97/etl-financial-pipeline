from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def upsert_raw_prices(engine: Engine, rows: list[dict[str, Any]]) -> int:
    """Insert raw OHLCV rows; skip duplicates (symbol + date)."""
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TEMP TABLE tmp_prices (LIKE raw.daily_prices INCLUDING ALL) ON COMMIT DROP
        """))
        df.to_sql("tmp_prices", conn, if_exists="append", index=False)
        result = conn.execute(text("""
            INSERT INTO raw.daily_prices (symbol, date, open, high, low, close, volume)
            SELECT symbol, date, open, high, low, close, volume FROM tmp_prices
            ON CONFLICT (symbol, date) DO NOTHING
        """))
    inserted = result.rowcount
    logger.info("Upserted %d raw price rows", inserted)
    return inserted


def upsert_analytics_metrics(engine: Engine, df: pd.DataFrame) -> int:
    """Insert computed metrics rows; update on conflict."""
    if df.empty:
        return 0
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TEMP TABLE tmp_metrics (LIKE analytics.price_metrics INCLUDING ALL) ON COMMIT DROP
        """))
        df.to_sql("tmp_metrics", conn, if_exists="append", index=False)
        result = conn.execute(text("""
            INSERT INTO analytics.price_metrics
                (symbol, date, close, ma_7, ma_21, ma_50, volatility_21, daily_return, cumulative_return)
            SELECT symbol, date, close, ma_7, ma_21, ma_50, volatility_21, daily_return, cumulative_return
            FROM tmp_metrics
            ON CONFLICT (symbol, date) DO UPDATE SET
                close = EXCLUDED.close,
                ma_7 = EXCLUDED.ma_7,
                ma_21 = EXCLUDED.ma_21,
                ma_50 = EXCLUDED.ma_50,
                volatility_21 = EXCLUDED.volatility_21,
                daily_return = EXCLUDED.daily_return,
                cumulative_return = EXCLUDED.cumulative_return,
                calculated_at = NOW()
        """))
    inserted = result.rowcount
    logger.info("Upserted %d analytics metric rows", inserted)
    return inserted
