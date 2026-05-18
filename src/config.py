from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    alpha_vantage_api_key: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "financial_db"
    postgres_user: str = "postgres"
    postgres_password: str = "changeme"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def database_url(self) -> str:
        base = (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        # Cloud DBs require SSL; localhost does not
        if self.postgres_host != "localhost":
            base += "?sslmode=require"
        return base

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
