"""
One-time bootstrap script for the Render PostgreSQL database.
Run this locally after creating the Render database, before deploying the API.

Usage:
    # Set the Render DB credentials in your local .env.render (or pass via env vars)
    POSTGRES_HOST=<render-host> \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=financial_db \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=<render-password> \
    ALPHA_VANTAGE_API_KEY=<your-key> \
    python scripts/bootstrap_render.py
"""
import sys
from pathlib import Path

# Allow importing from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.loaders.postgres_loader import get_engine
from src.connectors.alpha_vantage import AlphaVantageClient
from src.transformations.metrics import compute_metrics
from src.loaders.postgres_loader import upsert_raw_prices, upsert_analytics_metrics

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
SCHEMA_FILE = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"


def apply_schema(engine) -> None:
    sql = SCHEMA_FILE.read_text()
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute(sql)
        raw_conn.commit()
        print("Schema applied.")
    finally:
        raw_conn.close()


def run_pipeline(engine) -> None:
    client = AlphaVantageClient(api_key=settings.alpha_vantage_api_key)
    for symbol in SYMBOLS:
        print(f"Ingesting {symbol}...")
        rows = client.get_daily_prices(symbol, outputsize="compact")
        upsert_raw_prices(engine, rows)

        import pandas as pd
        raw_conn = engine.raw_connection()
        try:
            df = pd.read_sql(
                "SELECT symbol, date, open, high, low, close, volume "
                "FROM raw.daily_prices WHERE symbol = %s ORDER BY date",
                raw_conn,
                params=(symbol,),
            )
        finally:
            raw_conn.close()

        metrics_df = compute_metrics(df)
        upsert_analytics_metrics(engine, metrics_df)
        print(f"  {symbol}: {len(rows)} rows ingested, {len(metrics_df)} metrics computed.")


if __name__ == "__main__":
    print(f"Connecting to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    engine = get_engine(settings.database_url)
    apply_schema(engine)
    run_pipeline(engine)
    print("Bootstrap complete. The API is ready to serve data.")
