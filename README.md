# etl-financial-pipeline

![CI](https://github.com/PabloAMoreno97/etl-financial-pipeline/actions/workflows/ci.yml/badge.svg)

End-to-end batch ETL pipeline that ingests daily stock price data from **Alpha Vantage**, computes financial metrics, stores results in **PostgreSQL** (raw + analytics schema), and exposes the data via a **FastAPI** REST API — orchestrated with **Apache Airflow**.

**Live API:** https://etl-financial-api.onrender.com/docs

## Architecture

```
Alpha Vantage API
      │
      ▼
 [Airflow DAG]  ── runs weekdays at 18:00 UTC (after US market close)
      │
      ├─► PostgreSQL · raw.daily_prices         ← OHLCV as-received
      │         (Neon — serverless PostgreSQL)
      └─► PostgreSQL · analytics.price_metrics  ← MA7/21/50, volatility, returns
                                │
                                ▼
                     FastAPI REST API (Render)
                  GET /prices/raw/{symbol}
                  GET /prices/metrics/{symbol}
                  GET /prices/symbols
```

## Stack

| Layer | Technology |
|---|---|
| Data source | Alpha Vantage (free tier) |
| Transformation | Pandas — rolling metrics, pct_change |
| Storage | PostgreSQL (Neon) — schemas `raw` / `analytics` |
| Orchestration | Apache Airflow 2.10 (LocalExecutor, Docker) |
| API | FastAPI + Pydantic v2 + Uvicorn |
| Infra (local) | Docker Compose |
| Infra (cloud) | Render (API) + Neon (PostgreSQL) |
| Tests | Pytest — unit (transformations) + integration (API) |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/prices/symbols` | List available symbols |
| `GET` | `/prices/raw/{symbol}` | Daily OHLCV data |
| `GET` | `/prices/metrics/{symbol}` | Computed analytics metrics |

Query params: `start`, `end` (date), `limit` (max 500).

```bash
# Examples
curl "https://etl-financial-api.onrender.com/prices/symbols"
curl "https://etl-financial-api.onrender.com/prices/raw/AAPL?limit=10"
curl "https://etl-financial-api.onrender.com/prices/metrics/MSFT?start=2024-01-01"
```

## Getting started locally

### Prerequisites

- Docker + Docker Compose
- An [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key) (free)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env: set ALPHA_VANTAGE_API_KEY, POSTGRES_PASSWORD, and Airflow keys
```

Generate Airflow Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Start services

```bash
docker compose up -d
```

| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 (admin / admin) |
| FastAPI docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 3. Trigger the pipeline

In the Airflow UI: `DAGs → financial_pipeline → Trigger DAG ▶`

Or wait for the daily schedule (weekdays 18:00 UTC).

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Project structure

```
etl-financial-pipeline/
├── dags/
│   └── financial_pipeline_dag.py   # Airflow DAG — daily, 5 symbols
├── src/
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── connectors/
│   │   └── alpha_vantage.py        # API client with throttling + retry
│   ├── transformations/
│   │   └── metrics.py              # MA7/21/50, volatility, returns
│   ├── loaders/
│   │   └── postgres_loader.py      # Upsert via psycopg2 execute_values
│   └── api/
│       ├── main.py
│       ├── dependencies.py
│       └── routers/prices.py       # GET /raw, /metrics, /symbols
├── migrations/
│   └── 001_initial_schema.sql      # raw + analytics schemas
├── scripts/
│   ├── bootstrap_render.py         # One-time data seed for production
│   └── start.sh                    # Docker entrypoint (migrate + serve)
├── tests/
│   ├── conftest.py
│   ├── unit/test_metrics.py        # 7 unit tests on transformations
│   └── integration/test_api.py     # API tests with SQLite in-memory
├── docker-compose.yml              # postgres + airflow + api
├── Dockerfile                      # API container
├── Dockerfile.airflow              # Airflow + custom deps
└── render.yaml                     # Render deploy blueprint
```

## Design decisions

- **Two-schema approach (`raw` → `analytics`):** raw data is immutable once ingested; the analytics layer is fully recomputable from raw at any time.
- **Upsert via `execute_values`:** bypasses the SQLAlchemy/pandas version mismatch between Airflow (SA 1.4) and the API container (SA 2.0). Psycopg2 native batch insert is also faster than `to_sql`.
- **Idempotent DAG:** `ON CONFLICT DO NOTHING / DO UPDATE` makes reruns safe without duplicating data.
- **Throttling + retry (`tenacity`):** Alpha Vantage free tier limits 5 req/min — the connector handles this transparently with exponential backoff.
- **Neon for production DB:** serverless PostgreSQL with IPv4 support, no expiry on free tier. Airflow stays local; only the API is cloud-deployed.
