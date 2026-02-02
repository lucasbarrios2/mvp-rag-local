"""
Configuracao Centralizada - MVP RAG Local
Gemini + PostgreSQL + Qdrant
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuracoes do sistema.
    Carrega de variaveis de ambiente ou .env
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # GOOGLE GEMINI
    # ========================================================================

    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-preview-05-20"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768

    # ========================================================================
    # POSTGRESQL
    # ========================================================================

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "video_assets"
    postgres_user: str = "curator"
    postgres_password: str = "curator_pass_2026"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ========================================================================
    # QDRANT
    # ========================================================================

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "videos"

    # ========================================================================
    # UPLOAD
    # ========================================================================

    upload_dir: str = "./uploads"
    max_video_size_mb: int = 500

    def ensure_dirs(self):
        """Cria diretorios necessarios."""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
