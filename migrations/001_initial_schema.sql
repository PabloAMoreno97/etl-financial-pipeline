-- Raw layer: stores data exactly as received from Alpha Vantage
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.daily_prices (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(10)    NOT NULL,
    date        DATE           NOT NULL,
    open        NUMERIC(12, 4) NOT NULL,
    high        NUMERIC(12, 4) NOT NULL,
    low         NUMERIC(12, 4) NOT NULL,
    close       NUMERIC(12, 4) NOT NULL,
    volume      BIGINT         NOT NULL,
    ingested_at TIMESTAMP      NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_raw_prices_symbol_date ON raw.daily_prices (symbol, date DESC);

-- Analytics layer: computed metrics derived from raw data
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.price_metrics (
    id                SERIAL PRIMARY KEY,
    symbol            VARCHAR(10)     NOT NULL,
    date              DATE            NOT NULL,
    close             NUMERIC(12, 4)  NOT NULL,
    ma_7              NUMERIC(12, 4),
    ma_21             NUMERIC(12, 4),
    ma_50             NUMERIC(12, 4),
    volatility_21     NUMERIC(12, 6),
    daily_return      NUMERIC(12, 6),
    cumulative_return NUMERIC(12, 6),
    calculated_at     TIMESTAMP       NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_metrics_symbol_date ON analytics.price_metrics (symbol, date DESC);
