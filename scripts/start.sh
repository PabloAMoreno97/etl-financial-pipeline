#!/bin/sh
set -e

echo "Applying database schema..."
python -c "
import sys
sys.path.insert(0, '/app')
from src.config import settings
from src.loaders.postgres_loader import get_engine

engine = get_engine(settings.database_url)
schema = open('/app/migrations/001_initial_schema.sql').read()
conn = engine.raw_connection()
try:
    with conn.cursor() as cur:
        cur.execute(schema)
    conn.commit()
    print('Schema ready.')
finally:
    conn.close()
"

echo "Starting API..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
