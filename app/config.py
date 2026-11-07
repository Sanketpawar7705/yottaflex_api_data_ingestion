import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str = "http://127.0.0.1:8000"
    api_token: str = "local-demo-token"      
    database_path: str = "data/ingestion.db"
    page_size: int = 100
    max_retries: int = 4
    lookback_seconds: int = 3600              
    request_timeout: float = 10.0
    backoff_base: float = 0.25
    customer_lookup: str = "memory"           

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            api_base_url=env.get("API_BASE_URL", cls.api_base_url),
            api_token=env.get("API_TOKEN", cls.api_token),
            database_path=env.get("DATABASE_PATH", cls.database_path),
            page_size=int(env.get("PAGE_SIZE", cls.page_size)),
            max_retries=int(env.get("MAX_RETRIES", cls.max_retries)),
            lookback_seconds=int(env.get("LOOKBACK_SECONDS", cls.lookback_seconds)),
        )
