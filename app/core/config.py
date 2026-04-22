from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://tfg_user:tfg_password@localhost:5432/tfg_emails"
    API_KEY: Optional[str] = ""
    DEFAULT_ENGINE: Literal["keywords", "gemini"] = "gemini"

    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    CONFIDENCE_THRESHOLD: float = 0.6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

CATEGORIES = {
    "trabajo": "TFG/Trabajo",
    "universidad": "TFG/Universidad",
    "facturas": "TFG/Facturas",
    "promociones": "TFG/Promociones",
    "personal": "TFG/Personal",
    "phishing": "TFG/Phishing",
    "revisar": "TFG/Revisar",
}