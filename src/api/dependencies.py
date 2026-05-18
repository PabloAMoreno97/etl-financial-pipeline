from functools import lru_cache
from sqlalchemy.engine import Engine
from src.config import settings
from src.loaders.postgres_loader import get_engine


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    return get_engine(settings.database_url)
