from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Database
    postgres_dsn: str = "postgresql://vigie:vigie@localhost:5432/vigie"

    # Cache
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "vigie_mitre"

    # Langfuse
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Mailtrap
    mailtrap_api_token: str = ""
    mailtrap_from_email: str = "soc@atlasmetaux.fr"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    session_secret_key: str = ""


settings = Settings()
