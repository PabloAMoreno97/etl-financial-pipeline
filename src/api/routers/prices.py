from __future__ import annotations

from datetime import date
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.api.dependencies import get_db_engine

router = APIRouter(prefix="/prices", tags=["prices"])


class RawPriceRecord(BaseModel):
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class MetricsRecord(BaseModel):
    symbol: str
    date: date
    close: float
    ma_7: float | None
    ma_21: float | None
    ma_50: float | None
    volatility_21: float | None
    daily_return: float | None
    cumulative_return: float | None


@router.get("/raw/{symbol}", response_model=list[RawPriceRecord])
def get_raw_prices(
    symbol: str,
    engine: Annotated[Engine, Depends(get_db_engine)],
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, le=500),
):
    """Daily OHLCV data from the raw schema."""
    query = "SELECT * FROM raw.daily_prices WHERE symbol = :symbol"
    params: dict = {"symbol": symbol.upper()}
    if start:
        query += " AND date >= :start"
        params["start"] = start
    if end:
        query += " AND date <= :end"
        params["end"] = end
    query += " ORDER BY date DESC LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")
    return df.to_dict(orient="records")


@router.get("/metrics/{symbol}", response_model=list[MetricsRecord])
def get_metrics(
    symbol: str,
    engine: Annotated[Engine, Depends(get_db_engine)],
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, le=500),
):
    """Computed analytics metrics (MA, volatility, returns)."""
    query = "SELECT * FROM analytics.price_metrics WHERE symbol = :symbol"
    params: dict = {"symbol": symbol.upper()}
    if start:
        query += " AND date >= :start"
        params["start"] = start
    if end:
        query += " AND date <= :end"
        params["end"] = end
    query += " ORDER BY date DESC LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No metrics found for symbol '{symbol}'")
    return df.to_dict(orient="records")


@router.get("/symbols")
def list_symbols(engine: Annotated[Engine, Depends(get_db_engine)]):
    """List all symbols available in the database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT symbol FROM raw.daily_prices ORDER BY symbol"))
        symbols = [row[0] for row in result]
    return {"symbols": symbols}
