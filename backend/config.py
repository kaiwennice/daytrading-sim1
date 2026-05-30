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

    # Market data (OKX crypto spot) — top 50 by market cap (stablecoins excluded)
    symbols: list[str] = [
        "BTC-USDT",  "ETH-USDT",  "BNB-USDT",  "SOL-USDT",  "XRP-USDT",
        "DOGE-USDT", "TON-USDT",  "ADA-USDT",  "TRX-USDT",  "AVAX-USDT",
        "SHIB-USDT", "LINK-USDT", "DOT-USDT",  "BCH-USDT",  "NEAR-USDT",
        "UNI-USDT",  "LTC-USDT",  "APT-USDT",  "ICP-USDT",  "SUI-USDT",
        "ETC-USDT",  "FIL-USDT",  "ARB-USDT",  "OP-USDT",   "ATOM-USDT",
        "VET-USDT",  "HBAR-USDT", "MKR-USDT",  "GRT-USDT",  "ALGO-USDT",
        "XLM-USDT",  "AAVE-USDT", "INJ-USDT",  "WLD-USDT",  "SEI-USDT",
        "EGLD-USDT", "CRV-USDT",  "LDO-USDT",  "PEPE-USDT", "FLOKI-USDT",
        "STX-USDT",  "IMX-USDT",  "MANA-USDT", "SAND-USDT", "EOS-USDT",
        "TIA-USDT",  "WIF-USDT",  "JUP-USDT",  "SNX-USDT",  "PYTH-USDT",
    ]
    timeframes: list[str] = ["1m", "5m", "15m", "1H"]
    taker_fee: Decimal = Decimal("0.0005")
    okx_rest_base: str = "https://www.okx.com"
    okx_public_ws: str = "wss://ws.okx.com:8443/ws/v5/public"
    okx_business_ws: str = "wss://ws.okx.com:8443/ws/v5/business"


settings = Settings()
