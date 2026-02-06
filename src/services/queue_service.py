"""
QueueService - Fila de processamento de videos com worker em background.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class QueueTask:
    """Item da fila de processamento."""

    id: int
    video_id: int
    status: str
    priority: int
    attempts: int
    max_attempts: int
    error_message: Optional[str]
    created_at: datetime


@dataclass
class QueueStats:
    """Estatisticas da fila."""

    pending: int
    processing: int
    completed: int
    failed: int
    total: int


class QueueService:
    """
    Servico de fila de processamento com suporte a worker em background.

    Usa PostgreSQL como backend da fila com SELECT FOR UPDATE SKIP LOCKED
    para garantir processamento thread-safe.
    """

    def __init__(self, db_url: str, worker_id: Optional[str] = None):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._processor: Optional[Callable[[QueueTask], None]] = None

    def _ensure_table(self) -> None:
        """Cria tabela de fila se nao existir."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id SERIAL PRIMARY KEY,
                    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                    status VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                    priority INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    error_message TEXT,
                    locked_at TIMESTAMP,
                    locked_by VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    UNIQUE(video_id)
                )
            """
                )
            )
            conn.commit()

    def enqueue(self, video_id: int, priority: int = 0) -> Optional[int]:
        """
        Adiciona video a fila de processamento.

        Returns:
            ID do item na fila ou None se ja existir
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                INSERT INTO processing_queue (video_id, priority, status)
                VALUES (:video_id, :priority, 'pending')
                ON CONFLICT (video_id) DO NOTHING
                RETURNING id
            """
                ),
                {"video_id": video_id, "priority": priority},
            )
            conn.commit()
            row = result.fetchone()
            return row[0] if row else None

    def claim_next(self, lock_timeout_minutes: int = 10) -> Optional[QueueTask]:
        """
        Pega o proximo item pendente da fila de forma thread-safe.

        Usa SELECT FOR UPDATE SKIP LOCKED para evitar race conditions.
        Tambem recupera itens que estao locked ha mais tempo que o timeout.

        Returns:
            QueueTask ou None se fila estiver vazia
        """
        lock_timeout = datetime.utcnow() - timedelta(minutes=lock_timeout_minutes)

        with self.engine.connect() as conn:
            # Usar transacao explicita
            trans = conn.begin()
            try:
                # Buscar proximo item: pendente OU locked expirado
                result = conn.execute(
                    text(
                        """
                    SELECT id, video_id, status, priority, attempts, max_attempts,
                           error_message, created_at
                    FROM processing_queue
                    WHERE (status = 'pending' AND attempts < max_attempts)
                       OR (status = 'processing' AND locked_at < :lock_timeout)
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """
                    ),
                    {"lock_timeout": lock_timeout},
                )
                row = result.fetchone()

                if not row:
                    trans.commit()
                    return None

                # Marcar como processing e atualizar lock
                conn.execute(
                    text(
                        """
                    UPDATE processing_queue
                    SET status = 'processing',
                        locked_at = NOW(),
                        locked_by = :worker_id,
                        attempts = attempts + 1
                    WHERE id = :id
                """
                    ),
                    {"id": row[0], "worker_id": self.worker_id},
                )
                trans.commit()

                return QueueTask(
                    id=row[0],
                    video_id=row[1],
                    status="processing",
                    priority=row[3],
                    attempts=row[4] + 1,  # Ja incrementamos
                    max_attempts=row[5],
                    error_message=row[6],
                    created_at=row[7],
                )

            except Exception:
                trans.rollback()
                raise

    def complete(self, queue_id: int) -> None:
        """Marca item como concluido com sucesso."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    """
                UPDATE processing_queue
                SET status = 'completed',
                    completed_at = NOW(),
                    locked_at = NULL,
                    locked_by = NULL,
                    error_message = NULL
                WHERE id = :id
            """
                ),
                {"id": queue_id},
            )
            conn.commit()

    def fail(self, queue_id: int, error_message: str) -> None:
        """
        Marca item como falho.
        Se ainda tiver tentativas restantes, volta para pending.
        """
        with self.engine.connect() as conn:
            # Verificar se ainda tem tentativas
            result = conn.execute(
                text(
                    """
                SELECT attempts, max_attempts FROM processing_queue WHERE id = :id
            """
                ),
                {"id": queue_id},
            )
            row = result.fetchone()

            if row and row[0] < row[1]:
                # Ainda tem tentativas - voltar para pending
                new_status = "pending"
            else:
                # Esgotou tentativas
                new_status = "failed"

            conn.execute(
                text(
                    """
                UPDATE processing_queue
                SET status = :status,
                    error_message = :error,
                    locked_at = NULL,
                    locked_by = NULL
                WHERE id = :id
            """
                ),
                {"id": queue_id, "status": new_status, "error": error_message},
            )
            conn.commit()

    def retry(self, video_id: int) -> bool:
        """
        Reenfileira um video para nova tentativa (failed ou completed).

        Args:
            video_id: ID do video (nao o queue_id)

        Returns:
            True se o video foi reenfileirado, False se nao encontrado
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                UPDATE processing_queue
                SET status = 'pending',
                    attempts = 0,
                    error_message = NULL,
                    locked_at = NULL,
                    locked_by = NULL
                WHERE video_id = :video_id AND status IN ('failed', 'completed')
                RETURNING id
            """
                ),
                {"video_id": video_id},
            )
            conn.commit()
            return result.fetchone() is not None

    def get_stats(self) -> QueueStats:
        """Retorna estatisticas da fila."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) as total
                FROM processing_queue
            """
                )
            )
            row = result.fetchone()
            return QueueStats(
                pending=row[0] or 0,
                processing=row[1] or 0,
                completed=row[2] or 0,
                failed=row[3] or 0,
                total=row[4] or 0,
            )

    def get_queue_items(
        self, status: Optional[str] = None, limit: int = 50
    ) -> list[QueueTask]:
        """Lista itens da fila."""
        with self.engine.connect() as conn:
            if status:
                result = conn.execute(
                    text(
                        """
                    SELECT id, video_id, status, priority, attempts, max_attempts,
                           error_message, created_at
                    FROM processing_queue
                    WHERE status = :status
                    ORDER BY priority DESC, created_at ASC
                    LIMIT :limit
                """
                    ),
                    {"status": status, "limit": limit},
                )
            else:
                result = conn.execute(
                    text(
                        """
                    SELECT id, video_id, status, priority, attempts, max_attempts,
                           error_message, created_at
                    FROM processing_queue
                    ORDER BY created_at DESC
                    LIMIT :limit
                """
                    ),
                    {"limit": limit},
                )

            return [
                QueueTask(
                    id=row[0],
                    video_id=row[1],
                    status=row[2],
                    priority=row[3],
                    attempts=row[4],
                    max_attempts=row[5],
                    error_message=row[6],
                    created_at=row[7],
                )
                for row in result.fetchall()
            ]

    def start_worker(
        self,
        processor: Callable[[QueueTask], None],
        poll_interval: float = 5.0,
    ) -> None:
        """
        Inicia worker thread para processar fila em background.

        Args:
            processor: Funcao que processa cada item da fila
            poll_interval: Intervalo em segundos entre polls da fila
        """
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("Worker ja esta rodando")
            return

        self._processor = processor
        self._stop_event.clear()

        def worker_loop():
            logger.info(f"Worker {self.worker_id} iniciado")
            while not self._stop_event.is_set():
                try:
                    task = self.claim_next()
                    if task:
                        logger.info(
                            f"Processando video_id={task.video_id} "
                            f"(tentativa {task.attempts}/{task.max_attempts})"
                        )
                        try:
                            self._processor(task)
                            self.complete(task.id)
                            logger.info(f"Video {task.video_id} processado com sucesso")
                        except Exception as e:
                            error_msg = str(e)[:500]
                            logger.error(
                                f"Erro processando video {task.video_id}: {error_msg}"
                            )
                            self.fail(task.id, error_msg)
                    else:
                        # Fila vazia - aguardar
                        self._stop_event.wait(poll_interval)
                except Exception as e:
                    logger.error(f"Erro no worker loop: {e}")
                    self._stop_event.wait(poll_interval)

            logger.info(f"Worker {self.worker_id} finalizado")

        self._worker_thread = threading.Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()

    def stop_worker(self, timeout: float = 10.0) -> None:
        """Para o worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            self._stop_event.set()
            self._worker_thread.join(timeout=timeout)

    def is_worker_running(self) -> bool:
        """Verifica se worker esta ativo."""
        return self._worker_thread is not None and self._worker_thread.is_alive()
