# etl-financial-pipeline

End-to-end batch ETL pipeline that ingests daily stock price data from **Alpha Vantage**, computes financial metrics, stores results in **PostgreSQL** (raw + analytics schema), and exposes the data via a **FastAPI** REST API — orchestrated with **Apache Airflow**.

## Architecture

```
Alpha Vantage API
      │
      ▼
 [Airflow DAG]  ── runs weekdays at 18:00 UTC (after US market close)
      │
      ├─► PostgreSQL · raw.daily_prices         ← OHLCV as-received
      │
      └─► PostgreSQL · analytics.price_metrics  ← MA7/21/50, volatility, returns
                                │
                                ▼
                          FastAPI REST API
                       GET /prices/raw/{symbol}
                       GET /prices/metrics/{symbol}
                       GET /prices/symbols
```

## Stack

| Layer | Technology |
|---|---|
| Data source | Alpha Vantage (free tier) |
| Transformation | Pandas — rolling metrics, pct_change |
| Storage | PostgreSQL 16 — schemas `raw` / `analytics` |
| Orchestration | Apache Airflow 2.10 (LocalExecutor) |
| API | FastAPI + Pydantic v2 + Uvicorn |
| Infra | Docker Compose |
| Tests | Pytest — unit (transformations) + integration (API) |

## Getting started

### Prerequisites

- Docker + Docker Compose
- An [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key) (free)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and set your ALPHA_VANTAGE_API_KEY and a secure POSTGRES_PASSWORD
```

Generate Airflow keys:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste the result as AIRFLOW__CORE__FERNET_KEY in .env
```

### 2. Start services

```bash
docker compose up -d
```

Services:
- **PostgreSQL** → `localhost:5432`
- **Airflow webserver** → `http://localhost:8080` (user: `admin`, password: `admin`)
- **FastAPI** → `http://localhost:8000` (docs at `/docs`)

### 3. Trigger the pipeline

Either wait for the daily schedule or trigger manually from the Airflow UI:
`DAGs → financial_pipeline → Trigger DAG`

### 4. Query the API

```bash
# Last 100 days of AAPL raw prices
curl "http://localhost:8000/prices/raw/AAPL"

# Analytics metrics with date range
curl "http://localhost:8000/prices/metrics/MSFT?start=2024-01-01&end=2024-06-30"

# Available symbols
curl "http://localhost:8000/prices/symbols"
```

## Running tests locally

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Design decisions

- **Two-schema approach (`raw` → `analytics`):** raw data is immutable once ingested; the analytics layer is fully recomputable from raw at any time.
- **Upsert pattern (`ON CONFLICT DO NOTHING / DO UPDATE`):** the DAG is idempotent — safe to re-run without duplicating data.
- **Retry with exponential backoff (`tenacity`):** Alpha Vantage free tier has strict rate limits; the connector handles transient failures transparently.
- **LocalExecutor in Airflow:** sufficient for a single-machine setup; swap to CeleryExecutor + Redis for distributed workers in production.
