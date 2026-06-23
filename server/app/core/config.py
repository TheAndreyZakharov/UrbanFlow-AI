from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "UrbanFlow AI"
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    overpass_api_url: str = "https://overpass-api.de/api/interpreter"

    osm_cache_dir: Path = PROJECT_ROOT / "data" / "osm"
    sessions_dir: Path = PROJECT_ROOT / "data" / "sessions"
    model_dir: Path = PROJECT_ROOT / "data" / "models"
    runs_dir: Path = PROJECT_ROOT / "data" / "runs"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="URBANFLOW_",
        extra="ignore",
    )


settings = Settings()