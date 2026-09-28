import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "DEVELOPMENT"
    DEBUG: bool = True
    APP_NAME: str = "Bourlemont Champagne Bar POS"
    SECRET_KEY: str = "bourlemont-ultra-secret-key-change-in-production-sacatepequez"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/bourlemont_pos"
    FALLBACK_TO_SQLITE: bool = True
    SQLITE_URL: str = "sqlite:///./bourlemont.db"
    
    # Facturación Electrónica SAT / Infile
    FEL_PROVIDER: str = "MOCK"  # 'MOCK' o 'INFILE'
    FEL_NIT_EMITTER: str = "98765432-1"
    FEL_USER_PREFIX_WS: str = "BOURLEMONT_POS_WS"
    FEL_KEY_WS: str = "4B8F3D7A2C1E9087654321FEEDFACE00"
    FEL_PREFIX_UNIQUE_IDENTIFIER: str = "BLM"
    
    # Políticas de Bar
    ALLOW_NEGATIVE_STOCK: bool = True
    DEFAULT_TAX_RATE: float = 0.12  # IVA 12% en Guatemala
    DEFAULT_CURRENCY: str = "GTQ"
    CURRENCY_SYMBOL: str = "Q"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
