import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    USE_FIRESTORE_EMULATOR: bool = False
    FIRESTORE_EMULATOR_HOST: str = "localhost:8080"
    
    EMBEDDING_PROVIDER: str = "mock"  # 'openai', 'gemini', 'mock'
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Nodutgang for admin-anrop. Lamnas tom ar master-vagen helt avstangd.
    # Far ALDRIG ha ett defaultvarde i koden - repot ar publikt.
    MASTER_ADMIN_KEY: Optional[str] = None

    # Cloud Logging is the primary usage source. Enable only when an explicit
    # duplicate per-call Firestore archive is worth the extra write cost.
    STORE_USAGE_IN_FIRESTORE: bool = False

    MCP_SERVER_NAME: str = "mcp-las"
    MCP_SERVER_PORT: int = 8000

settings = Settings()
