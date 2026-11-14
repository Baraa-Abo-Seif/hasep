import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Info
    APP_NAME: str = "# hasep Financial Form AI"
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "aya-secret-key-development-minimum-32-chars-long"
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"

    # Timezone & Form Settings
    TIMEZONE: str = "Asia/Amman"
    PURCHASES_ROW_COUNT: int = 10
    EXPENSES_ROW_COUNT: int = 10
    EMPLOYEES_ROW_COUNT: int = 6

    # Database (SQLite local database; PostgreSQL in production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/app.db"

    # Storage
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    # Concurrency settings for document processing pipeline
    MAX_CONCURRENCY: int = 4  # Number of pages processed in parallel
    FAST_MODE: bool = False  # Skip heavy image preprocessing when True for speed
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,webp,pdf"
    RETENTION_DAYS: int = 30

    # Google Gemini API (Exclusive AI Provider)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Google OAuth 2.0 & Google Sheets Integration
    GOOGLE_OAUTH_CLIENT_SECRET_FILE: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_FRONTEND_REDIRECT: str = "http://localhost:5173/settings"
    GOOGLE_SPREADSHEET_ID: Optional[str] = None
    GOOGLE_SHEETS_ENABLED: bool = True
    GOOGLE_SCOPES: str = "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/userinfo.email openid"

    # Security & Encryption
    ENCRYPTION_KEY: str = "dGhpc2lzYTMydnl0ZWtleW11c3RiZTMyYnl0ZXNhZg=="
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower().lstrip(".") for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()}


settings = Settings()
