"""
Configuração Centralizada - MVP RAG Local
Gerencia todas as configurações usando Pydantic Settings
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações do sistema
    Carrega de variáveis de ambiente ou .env
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

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
        """Database URL para SQLAlchemy"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ========================================================================
    # QDRANT
    # ========================================================================

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None  # None para local sem auth

    qdrant_collection_name: str = "video_clips"
    qdrant_vector_size: int = 768  # CLIP ViT-L/14

    @property
    def qdrant_url(self) -> str:
        """Qdrant URL"""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    # ========================================================================
    # ANTHROPIC (CLAUDE)
    # ========================================================================

    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_max_tokens: int = 2048
    claude_temperature: float = 0.3

    # ========================================================================
    # CLIP (EMBEDDINGS)
    # ========================================================================

    clip_model_name: str = "openai/clip-vit-large-patch14"  # 768-dim
    # Alternativas:
    # - "openai/clip-vit-base-patch32"    # 512-dim, mais rápido
    # - "openai/clip-vit-large-patch14"   # 768-dim, melhor qualidade

    clip_device: str = "auto"  # "auto", "cuda", "cpu"

    # ========================================================================
    # PROCESSAMENTO DE VÍDEO
    # ========================================================================

    # Paths
    video_storage_path: Path = Path("/data/videos")
    frames_cache_path: Path = Path("/data/frames_cache")

    # Extração de frames
    max_frames_per_clip: int = 8
    scene_detection_threshold: float = 27.0  # PySceneDetect

    # Performance
    max_workers: int = 4
    batch_size: int = 10

    # ========================================================================
    # REDIS (CACHE & QUEUE)
    # ========================================================================

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        """Redis URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ========================================================================
    # CURADORIA (RAG)
    # ========================================================================

    # Query expansion
    enable_query_expansion: bool = True

    # Busca vetorial
    vector_search_limit: int = 100
    final_selection_limit: int = 30

    # MMR (Maximal Marginal Relevance)
    mmr_lambda: float = 0.7  # 1.0 = só relevância, 0.0 = só diversidade

    # Reranking
    enable_llm_reranking: bool = True
    rerank_top_k: int = 50

    # ========================================================================
    # LOGGING & MONITORING
    # ========================================================================

    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_format: str = "rich"  # "rich", "json", "simple"

    # Prometheus metrics
    enable_metrics: bool = False
    metrics_port: int = 9090

    # ========================================================================
    # DEVELOPMENT
    # ========================================================================

    debug: bool = False
    environment: str = "local"  # local, staging, production

    # ========================================================================
    # HELPERS
    # ========================================================================

    def ensure_dirs(self):
        """Cria diretórios necessários"""
        self.video_storage_path.mkdir(parents=True, exist_ok=True)
        self.frames_cache_path.mkdir(parents=True, exist_ok=True)

    def validate_settings(self) -> list[str]:
        """
        Valida configurações e retorna lista de erros
        """
        errors = []

        # Validar API keys
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY não configurada")

        # Validar conexões (tentar conectar)
        # ... implementar validação de DB, Qdrant, etc

        return errors


# ============================================================================
# INSTÂNCIA GLOBAL
# ============================================================================

settings = Settings()

# Criar diretórios na importação
settings.ensure_dirs()


# ============================================================================
# VALIDAÇÃO AO INICIAR
# ============================================================================

if __name__ == "__main__":
    print("🔧 Configurações do Sistema\n")
    print(f"PostgreSQL: {settings.postgres_url}")
    print(f"Qdrant: {settings.qdrant_url}")
    print(f"Claude Model: {settings.claude_model}")
    print(f"CLIP Model: {settings.clip_model_name}")
    print(f"Max Workers: {settings.max_workers}")
    print(f"Batch Size: {settings.batch_size}")
    print()

    # Validar
    errors = settings.validate_settings()
    if errors:
        print("❌ ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Todas as configurações OK!")
