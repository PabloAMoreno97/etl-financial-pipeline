"""
Integration tests for the FastAPI layer.
These tests use TestClient with a SQLite in-memory database (no Docker required).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from src.api.main import app
from src.api.dependencies import get_db_engine

SQLITE_URL = "sqlite:///:memory:"

TEST_DDL = """
CREATE TABLE IF NOT EXISTS "raw.daily_prices" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
CREATE TABLE IF NOT EXISTS "analytics.price_metrics" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL,
    ma_7 REAL, ma_21 REAL, ma_50 REAL,
    volatility_21 REAL, daily_return REAL, cumulative_return REAL,
    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
"""


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        for stmt in TEST_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    return engine


@pytest.fixture(scope="module")
def client(test_engine):
    app.dependency_overrides[get_db_engine] = lambda: test_engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_symbols_empty(client):
    response = client.get("/prices/symbols")
    assert response.status_code == 200
    assert response.json() == {"symbols": []}


def test_raw_prices_not_found(client):
    response = client.get("/prices/raw/AAPL")
    assert response.status_code == 404


def test_metrics_not_found(client):
    response = client.get("/prices/metrics/AAPL")
    assert response.status_code == 404
