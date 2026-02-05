"""
QdrantService - Indexacao e busca vetorial no Qdrant.
Suporta busca dual (visual + narrativa) com named vectors.
"""

from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    NamedVector,
    PointStruct,
    VectorParams,
)


# Nome da collection com vetores duplos
DUAL_COLLECTION_SUFFIX = "_dual"


@dataclass
class DualSearchResult:
    """Resultado de busca combinando visual e narrativa."""
    id: int
    visual_score: float
    narrative_score: float
    combined_score: float
    payload: dict


class QdrantService:
    def __init__(
        self,
        host: str,
        port: int,
        collection: str,
        vector_size: int,
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection = collection
        self.dual_collection = collection + DUAL_COLLECTION_SUFFIX
        self.vector_size = vector_size
        self._ensure_collection(vector_size)
        self._ensure_dual_collection(vector_size)

    def _ensure_collection(self, vector_size: int) -> None:
        """Cria collection legada se nao existir."""
        collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=vector_size, distance=Distance.COSINE
                ),
            )

    def _ensure_dual_collection(self, vector_size: int) -> None:
        """Cria collection com vetores duplos (visual + narrativa)."""
        collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.dual_collection not in collections:
            self.client.create_collection(
                collection_name=self.dual_collection,
                vectors_config={
                    "visual": VectorParams(size=vector_size, distance=Distance.COSINE),
                    "narrative": VectorParams(size=vector_size, distance=Distance.COSINE),
                },
            )

    def index_dual(
        self,
        video_id: int,
        visual_embedding: list[float],
        narrative_embedding: list[float],
        payload: dict,
    ) -> tuple[str, str]:
        """
        Indexa embeddings duplos (visual + narrativa).

        Returns:
            Tupla (visual_id, narrative_id)
        """
        point_id = video_id
        self.client.upsert(
            collection_name=self.dual_collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector={
                        "visual": visual_embedding,
                        "narrative": narrative_embedding,
                    },
                    payload=payload,
                )
            ],
        )
        return (f"{point_id}_visual", f"{point_id}_narrative")

    def search_dual(
        self,
        query_embedding: list[float],
        limit: int = 20,
        visual_weight: float = 0.5,
        narrative_weight: float = 0.5,
    ) -> list[DualSearchResult]:
        """
        Busca em ambos os vetores e combina resultados.

        Args:
            query_embedding: Embedding da query
            limit: Numero maximo de resultados
            visual_weight: Peso para score visual (0-1)
            narrative_weight: Peso para score narrativo (0-1)

        Returns:
            Lista de resultados ordenados por score combinado
        """
        # Buscar em visual
        visual_results = self.client.query_points(
            collection_name=self.dual_collection,
            query=NamedVector(name="visual", vector=query_embedding),
            limit=limit * 2,  # Buscar mais para ter margem na combinacao
            with_payload=True,
        )

        # Buscar em narrativa
        narrative_results = self.client.query_points(
            collection_name=self.dual_collection,
            query=NamedVector(name="narrative", vector=query_embedding),
            limit=limit * 2,
            with_payload=True,
        )

        # Combinar resultados
        scores = {}  # {id: {visual: score, narrative: score, payload: ...}}

        for hit in visual_results.points:
            scores[hit.id] = {
                "visual_score": hit.score,
                "narrative_score": 0.0,
                "payload": hit.payload,
            }

        for hit in narrative_results.points:
            if hit.id in scores:
                scores[hit.id]["narrative_score"] = hit.score
            else:
                scores[hit.id] = {
                    "visual_score": 0.0,
                    "narrative_score": hit.score,
                    "payload": hit.payload,
                }

        # Calcular score combinado e ordenar
        results = []
        for point_id, data in scores.items():
            combined = (
                data["visual_score"] * visual_weight +
                data["narrative_score"] * narrative_weight
            )
            results.append(DualSearchResult(
                id=point_id,
                visual_score=data["visual_score"],
                narrative_score=data["narrative_score"],
                combined_score=combined,
                payload=data["payload"],
            ))

        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:limit]

    def index(
        self,
        video_id: int,
        embedding: list[float],
        payload: dict,
    ) -> str:
        """Indexa embedding com metadata (legado). Retorna o point ID usado."""
        point_id = video_id
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return str(point_id)

    def search(
        self,
        query_embedding: list[float],
        limit: int = 20,
    ) -> list[dict]:
        """Busca vetorial por similaridade coseno (legado)."""
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results.points
        ]

    def delete(self, video_id: int) -> None:
        """Remove ponto do Qdrant (ambas collections)."""
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=[video_id],
            )
        except Exception:
            pass
        try:
            self.client.delete(
                collection_name=self.dual_collection,
                points_selector=[video_id],
            )
        except Exception:
            pass
