from pathlib import Path

from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_VOICE_SECURITY_PATH = PROJECT_ROOT / "VoiceSecurity"


class Settings(BaseSettings):
    PROJECT_NAME: str = "EchoGuard"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite+aiosqlite:///./echoguard.db"
    JWT_SECRET_KEY: str = "change_this_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    voice_security_path: str = str(DEFAULT_VOICE_SECURITY_PATH)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://192.168.137.216:5173",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
