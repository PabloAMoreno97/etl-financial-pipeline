"""
Seed Supabase with historical financial data from Alpha Vantage.
Run once before deploying to Render to pre-populate the database.

Reads connection settings from .env — POSTGRES_HOST must point to Supabase.
Uses 5 of the 25 daily free API requests (one per symbol).
Fetches last 100 trading days per symbol (free tier limit; full history is premium).
Total runtime: ~1 minute (Alpha Vantage throttling: 12 s/request).

Usage:
    pip install -r requirements.txt
    python scripts/seed_supabase.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.connectors.alpha_vantage import AlphaVantageClient
from src.loaders.postgres_loader import get_engine, upsert_analytics_metrics, upsert_raw_prices
from src.transformations.metrics import compute_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]


def seed() -> None:
    logger.info(
        "Target DB: %s:%s/%s", settings.postgres_host, settings.postgres_port, settings.postgres_db
    )
    engine = get_engine(settings.database_url)
    client = AlphaVantageClient(api_key=settings.alpha_vantage_api_key)

    for i, symbol in enumerate(SYMBOLS):
        logger.info("[%d/%d] %s — fetching full history...", i + 1, len(SYMBOLS), symbol)

        rows = client.get_daily_prices(symbol, outputsize="compact")
        if not rows:
            logger.warning("No data returned for %s, skipping", symbol)
            continue

        raw_count = upsert_raw_prices(engine, rows)
        logger.info("  raw rows upserted: %d", raw_count)

        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        metrics_df = compute_metrics(df)
        metrics_count = upsert_analytics_metrics(engine, metrics_df)
        logger.info("  metric rows upserted: %d", metrics_count)

    logger.info("Seed complete — all %d symbols processed.", len(SYMBOLS))


if __name__ == "__main__":
    seed()
