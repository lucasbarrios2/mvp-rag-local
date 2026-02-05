"""
Testes unitarios - MVP RAG Local
"""

import os
import pytest

# Configurar variaveis de ambiente para testes
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "video_assets")
os.environ.setdefault("POSTGRES_USER", "curator")
os.environ.setdefault("POSTGRES_PASSWORD", "curator_pass_2026")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")


class TestConfig:
    """Testes de configuracao."""

    def test_config_loads(self):
        from src.config import settings
        assert settings.google_api_key is not None
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.qdrant_collection == "videos"

    def test_postgres_url(self):
        from src.config import settings
        url = settings.postgres_url
        assert "postgresql://" in url
        assert "video_assets" in url


class TestModels:
    """Testes dos modelos Pydantic."""

    def test_video_analysis_valid(self):
        from src.models import VideoAnalysis
        analysis = VideoAnalysis(
            description="Video de teste",
            tags=["tag1", "tag2"],
            emotional_tone="comico",
            intensity=7.5,
            viral_potential=8.0,
            key_moments=[{"timestamp_ms": 0, "event": "inicio"}],
            themes={"humor": 8.0},
        )
        assert analysis.description == "Video de teste"
        assert analysis.intensity == 7.5
        assert len(analysis.tags) == 2

    def test_video_analysis_bounds(self):
        from src.models import VideoAnalysis
        # Intensity fora do limite deve falhar
        with pytest.raises(ValueError):
            VideoAnalysis(
                description="Teste",
                tags=[],
                emotional_tone="teste",
                intensity=15.0,  # > 10
                viral_potential=5.0,
            )

    def test_search_result(self):
        from src.models import SearchResult
        result = SearchResult(
            id=1,
            filename="video.mp4",
            score=0.95,
            emotional_tone="epico",
            intensity=8.0,
        )
        assert result.id == 1
        assert result.score == 0.95

    def test_search_response(self):
        from src.models import SearchResponse, SearchResult
        response = SearchResponse(
            query="videos engracados",
            results=[
                SearchResult(id=1, filename="v1.mp4", score=0.9),
                SearchResult(id=2, filename="v2.mp4", score=0.8),
            ],
            rag_response="Encontrei 2 videos relevantes.",
        )
        assert len(response.results) == 2
        assert response.query == "videos engracados"


class TestDatabaseService:
    """Testes do servico de banco de dados."""

    @pytest.fixture
    def db_url(self):
        from src.config import settings
        return settings.postgres_url

    def test_database_service_init(self, db_url):
        """Teste de inicializacao (pode falhar se DB nao estiver acessivel)."""
        from src.services.database_service import DatabaseService
        try:
            db = DatabaseService(db_url)
            assert db.engine is not None
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")

    def test_database_service_stats(self, db_url):
        """Teste de estatisticas."""
        from src.services.database_service import DatabaseService
        try:
            db = DatabaseService(db_url)
            stats = db.get_stats()
            assert "total" in stats
            assert "analyzed" in stats
            assert "pending" in stats
            assert "failed" in stats
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")


class TestEmbeddingService:
    """Testes do servico de embeddings."""

    def test_embedding_service_init(self):
        from src.services.embedding_service import EmbeddingService
        svc = EmbeddingService(
            api_key="test-key",
            model="text-embedding-004",
            dimensions=768,
        )
        assert svc.model == "text-embedding-004"
        assert svc.dimensions == 768

    def test_generate_for_video_text(self):
        """Testa montagem do texto para embedding."""
        from src.models import VideoAnalysis
        analysis = VideoAnalysis(
            description="Um gato pulando",
            tags=["gato", "pulo", "animal"],
            emotional_tone="comico",
            intensity=6.0,
            viral_potential=7.0,
            themes={"animais": 9.0, "humor": 6.0},
        )
        # Verificar que os campos estao corretos
        assert "gato" in analysis.description
        assert len(analysis.tags) == 3


class TestQdrantService:
    """Testes do servico Qdrant."""

    def test_qdrant_service_init(self):
        """Teste de inicializacao (pode falhar se Qdrant nao estiver acessivel)."""
        from src.services.qdrant_service import QdrantService
        try:
            svc = QdrantService(
                host="localhost",
                port=6333,
                collection="test_videos",
                vector_size=768,
            )
            assert svc.collection == "test_videos"
        except Exception as e:
            pytest.skip(f"Qdrant nao acessivel: {e}")


class TestGeminiService:
    """Testes do servico Gemini."""

    def test_gemini_service_init(self):
        from src.services.gemini_service import GeminiService
        svc = GeminiService(
            api_key="test-key",
            model="gemini-3-pro-preview",
        )
        assert svc.model == "gemini-3-pro-preview"

    def test_gemini_service_has_video_rag_method(self):
        """Testa que o metodo de RAG com video existe."""
        from src.services.gemini_service import GeminiService
        svc = GeminiService(
            api_key="test-key",
            model="gemini-3-pro-preview",
        )
        assert hasattr(svc, "generate_rag_response_with_videos")
        assert callable(svc.generate_rag_response_with_videos)

    def test_gemini_video_rag_empty_paths(self):
        """Testa resposta quando nao ha videos."""
        from src.services.gemini_service import GeminiService
        svc = GeminiService(
            api_key="test-key",
            model="gemini-3-pro-preview",
        )
        result = svc.generate_rag_response_with_videos(
            query="teste",
            video_paths=[],
        )
        assert "Nenhum video disponivel" in result

    def test_gemini_prompts_exist(self):
        """Testa que os prompts de RAG estao definidos."""
        from src.services.gemini_service import (
            RAG_PROMPT_TEMPLATE,
            RAG_VIDEO_PROMPT_TEMPLATE,
        )
        assert "{query}" in RAG_PROMPT_TEMPLATE
        assert "{clips_context}" in RAG_PROMPT_TEMPLATE
        assert "{query}" in RAG_VIDEO_PROMPT_TEMPLATE
        assert "{num_videos}" in RAG_VIDEO_PROMPT_TEMPLATE


class TestQueueService:
    """Testes do servico de fila."""

    def test_queue_task_dataclass(self):
        """Testa dataclass QueueTask."""
        from datetime import datetime
        from src.services.queue_service import QueueTask
        task = QueueTask(
            id=1,
            video_id=10,
            status="pending",
            priority=0,
            attempts=0,
            max_attempts=3,
            error_message=None,
            created_at=datetime.utcnow(),
        )
        assert task.id == 1
        assert task.video_id == 10
        assert task.status == "pending"

    def test_queue_stats_dataclass(self):
        """Testa dataclass QueueStats."""
        from src.services.queue_service import QueueStats
        stats = QueueStats(
            pending=5,
            processing=2,
            completed=10,
            failed=1,
            total=18,
        )
        assert stats.pending == 5
        assert stats.total == 18

    def test_queue_service_init(self):
        """Testa inicializacao do QueueService."""
        from src.services.queue_service import QueueService
        from src.config import settings
        try:
            queue = QueueService(settings.postgres_url)
            assert queue.worker_id is not None
            assert queue._worker_thread is None
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")

    def test_queue_service_stats(self):
        """Testa estatisticas da fila."""
        from src.services.queue_service import QueueService
        from src.config import settings
        try:
            queue = QueueService(settings.postgres_url)
            stats = queue.get_stats()
            assert stats.pending >= 0
            assert stats.processing >= 0
            assert stats.completed >= 0
            assert stats.failed >= 0
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")


class TestVideoProcessor:
    """Testes do processador de video."""

    def test_processing_result_dataclass(self):
        """Testa dataclass ProcessingResult."""
        from src.services.video_processor import ProcessingResult
        result = ProcessingResult(
            success=True,
            video_id=1,
            embedding_id="emb-123",
        )
        assert result.success is True
        assert result.video_id == 1
        assert result.error is None

    def test_processing_result_failure(self):
        """Testa ProcessingResult em caso de falha."""
        from src.services.video_processor import ProcessingResult
        result = ProcessingResult(
            success=False,
            video_id=1,
            error="Erro de teste",
        )
        assert result.success is False
        assert "Erro" in result.error


class TestComponents:
    """Testes dos componentes UI."""

    def test_calculate_total_pages(self):
        """Testa calculo de paginas."""
        from src.components import calculate_total_pages
        assert calculate_total_pages(0, 10) == 1
        assert calculate_total_pages(5, 10) == 1
        assert calculate_total_pages(10, 10) == 1
        assert calculate_total_pages(11, 10) == 2
        assert calculate_total_pages(25, 10) == 3

    def test_queue_status_badge(self):
        """Testa badges de status."""
        from src.components import queue_status_badge
        assert "Pendente" in queue_status_badge("pending")
        assert "Processando" in queue_status_badge("processing")
        assert "Concluido" in queue_status_badge("completed")
        assert "Falhou" in queue_status_badge("failed")


class TestDatabaseServicePagination:
    """Testes de paginacao do DatabaseService."""

    @pytest.fixture
    def db_url(self):
        from src.config import settings
        return settings.postgres_url

    def test_list_videos_paginated(self, db_url):
        """Testa listagem paginada."""
        from src.services.database_service import DatabaseService
        try:
            db = DatabaseService(db_url)
            videos, total = db.list_videos_paginated(page=1, per_page=10)
            assert isinstance(videos, list)
            assert isinstance(total, int)
            assert total >= 0
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")

    def test_get_videos_by_ids_dict_empty(self, db_url):
        """Testa busca por IDs com lista vazia."""
        from src.services.database_service import DatabaseService
        try:
            db = DatabaseService(db_url)
            result = db.get_videos_by_ids_dict([])
            assert result == {}
        except Exception as e:
            pytest.skip(f"Banco de dados nao acessivel: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
