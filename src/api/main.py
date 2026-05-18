from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import prices

app = FastAPI(
    title="Financial ETL API",
    description="Query historical price data and computed analytics metrics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(prices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
