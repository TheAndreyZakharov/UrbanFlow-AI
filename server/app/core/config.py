from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UrbanFlow AI"
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    overpass_api_url: str = "https://overpass-api.de/api/interpreter"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_prefix="URBANFLOW_",
        extra="ignore",
    )


settings = Settings()