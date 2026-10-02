"""
Application configuration.

All environment-driven settings live here, plus the global currency
reference lists that other modules (wallets, exchange rates, orders,
etc.) will import from a single source of truth.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General ---
    PROJECT_NAME: str = "Currency Platform API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12

    # --- Database (PostgreSQL) ---
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "app_db"

    # If set explicitly, this takes priority over the individual fields above.
    DATABASE_URL: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # Global currency reference lists.
    #
    # These are intentionally defined as module/class-level constants
    # (not DB rows) so every module — wallets, pricing, orders, KYC
    # limits, etc. — can import a single, consistent source of truth:
    #
    #   from app.core.config import FIAT_LIST, CRYPTO_LIST
    #
    # or, via the settings singleton:
    #
    #   from app.core.config import get_settings
    #   get_settings().FIAT_LIST
    # ------------------------------------------------------------------
    FIAT_LIST: List[str] = [
        "USD", "EUR", "GBP", "BDT", "INR", "AED", "CAD", "AUD",
    ]

    CRYPTO_LIST: List[str] = [
        "BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE", "MATIC",
    ]

    @property
    def SUPPORTED_CURRENCIES(self) -> List[str]:
        """Convenience union of fiat + crypto, useful for validators/enums."""
        return self.FIAT_LIST + self.CRYPTO_LIST


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import and call this instead of
    instantiating Settings() directly, so the whole app shares one instance."""
    return Settings()


settings = get_settings()

# Module-level re-exports for convenient direct imports elsewhere, e.g.:
#   from app.core.config import FIAT_LIST, CRYPTO_LIST
FIAT_LIST: List[str] = settings.FIAT_LIST
CRYPTO_LIST: List[str] = settings.CRYPTO_LIST
