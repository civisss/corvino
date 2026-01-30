"""
Corvino - Configuration
Centralized settings for the trading signals system.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database (DATABASE_URL overrides for Docker)
    database_url: str = "postgresql://corvino:corvino_secret@localhost:5432/corvino"
    # Optional: set in Docker as postgresql://user:pass@postgres:5432/dbname

    # Exchange: Binance USD-M Futures (solo dati pubblici, nessuna API key richiesta)
    # Per trading esecuzione servirebbero API; per OHLCV è sufficiente CCXT senza key

    # AI / LLM: Perplexity (market, signals, chart reading)
    perplexity_api_key: str = ""
    llm_model: str = "sonar"  # Perplexity: sonar, sonar-pro (used with base_url /v2)

    # News
    news_api_key: str = ""

    # Supported assets (Futures perpetual Binance USD-M) and timeframes
    # Supported assets (Futures perpetual Binance USD-M) and timeframes
    supported_assets: list[str] = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load supported assets from file if it exists
        try:
            with open("supported_assets.txt", "r") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    self.supported_assets = lines
        except FileNotFoundError:
            pass  # Keep defaults

    supported_timeframes: list[str] = ["1h", "2h", "4h", "1d"]
    timeframe_seconds: dict[str, int] = {
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "1d": 86400,
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
