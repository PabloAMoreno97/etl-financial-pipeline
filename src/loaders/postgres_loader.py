from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def upsert_raw_prices(engine: Engine, rows: list[dict[str, Any]]) -> int:
    """Batch-upsert raw OHLCV rows via psycopg2 execute_values (SA-version-agnostic)."""
    if not rows:
        return 0
    values = [
        (r["symbol"], r["date"], r["open"], r["high"], r["low"], r["close"], r["volume"])
        for r in rows
    ]
    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO raw.daily_prices (symbol, date, open, high, low, close, volume)
                VALUES %s
                ON CONFLICT (symbol, date) DO NOTHING
            """, values)
            inserted = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logger.info("Upserted %d raw price rows", inserted)
    return inserted


def upsert_analytics_metrics(engine: Engine, df: pd.DataFrame) -> int:
    """Batch-upsert computed metrics via psycopg2 execute_values (SA-version-agnostic)."""
    if df.empty:
        return 0
    values = [
        (
            row["symbol"], row["date"], row["close"],
            row["ma_7"], row["ma_21"], row["ma_50"],
            row["volatility_21"], row["daily_return"], row["cumulative_return"],
        )
        for _, row in df.iterrows()
    ]
    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO analytics.price_metrics
                    (symbol, date, close, ma_7, ma_21, ma_50, volatility_21, daily_return, cumulative_return)
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    close             = EXCLUDED.close,
                    ma_7              = EXCLUDED.ma_7,
                    ma_21             = EXCLUDED.ma_21,
                    ma_50             = EXCLUDED.ma_50,
                    volatility_21     = EXCLUDED.volatility_21,
                    daily_return      = EXCLUDED.daily_return,
                    cumulative_return = EXCLUDED.cumulative_return,
                    calculated_at     = NOW()
            """, values)
            inserted = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logger.info("Upserted %d analytics metric rows", inserted)
    return inserted


def read_prices_raw(engine: Engine, symbol: str) -> pd.DataFrame:
    """Read all raw prices for a symbol using a raw psycopg2 connection."""
    conn = engine.raw_connection()
    try:
        df = pd.read_sql(
            "SELECT symbol, date, open, high, low, close, volume "
            "FROM raw.daily_prices WHERE symbol = %s ORDER BY date",
            conn,
            params=(symbol,),
        )
    finally:
        conn.close()
    return df
