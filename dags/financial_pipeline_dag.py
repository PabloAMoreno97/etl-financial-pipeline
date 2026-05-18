"""
Daily financial ETL pipeline.
Ingests OHLCV data from Alpha Vantage → PostgreSQL raw schema,
then computes analytics metrics → PostgreSQL analytics schema.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

default_args = {
    "owner": "pablo",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def ingest_prices(symbol: str, **context) -> None:
    import sys
    sys.path.insert(0, "/opt/airflow")
    from src.connectors.alpha_vantage import AlphaVantageClient
    from src.loaders.postgres_loader import get_engine, upsert_raw_prices
    from src.config import settings

    client = AlphaVantageClient(api_key=settings.alpha_vantage_api_key)
    rows = client.get_daily_prices(symbol, outputsize="compact")
    engine = get_engine(settings.database_url)
    upsert_raw_prices(engine, rows)


def compute_and_load_metrics(symbol: str, **context) -> None:
    import sys
    import pandas as pd
    sys.path.insert(0, "/opt/airflow")
    from sqlalchemy import text
    from src.loaders.postgres_loader import get_engine, upsert_analytics_metrics
    from src.transformations.metrics import compute_metrics
    from src.config import settings

    engine = get_engine(settings.database_url)
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT * FROM raw.daily_prices WHERE symbol = :symbol ORDER BY date"),
            conn,
            params={"symbol": symbol},
        )
    if df.empty:
        logger.warning("No raw data found for %s, skipping metrics", symbol)
        return
    metrics_df = compute_metrics(df)
    upsert_analytics_metrics(engine, metrics_df)


with DAG(
    dag_id="financial_pipeline",
    default_args=default_args,
    description="Daily ETL: Alpha Vantage → PostgreSQL raw + analytics",
    schedule="0 18 * * 1-5",  # weekdays at 18:00 UTC (after US market close)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "finance"],
) as dag:
    for symbol in SYMBOLS:
        ingest_task = PythonOperator(
            task_id=f"ingest_{symbol.lower()}",
            python_callable=ingest_prices,
            op_kwargs={"symbol": symbol},
        )
        metrics_task = PythonOperator(
            task_id=f"metrics_{symbol.lower()}",
            python_callable=compute_and_load_metrics,
            op_kwargs={"symbol": symbol},
        )
        ingest_task >> metrics_task
