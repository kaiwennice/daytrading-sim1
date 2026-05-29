from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/daysim"
    jwt_secret: str = "dev-secret-change-me-to-a-long-random-string-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    cors_origins: list[str] = ["http://localhost:5173"]

    # SMTP — leave smtp_host empty to use console-log mode (development)
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_ssl: bool = True

    # Market data (OKX crypto spot)
    symbols: list[str] = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    timeframes: list[str] = ["1m", "5m", "15m", "1H"]
    taker_fee: Decimal = Decimal("0.0005")
    okx_rest_base: str = "https://www.okx.com"
    okx_public_ws: str = "wss://ws.okx.com:8443/ws/v5/public"
    okx_business_ws: str = "wss://ws.okx.com:8443/ws/v5/business"


settings = Settings()
