"""
QdrantService - Indexacao e busca vetorial no Qdrant.
Suporta busca dual (visual + narrativa) com named vectors.
"""

from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    NamedVector,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)


# Nome da collection com vetores duplos
DUAL_COLLECTION_SUFFIX = "_dual"
UNIFIED_COLLECTION_SUFFIX = "_unified"


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
        self.unified_collection = collection + UNIFIED_COLLECTION_SUFFIX
        self.vector_size = vector_size
        self._ensure_collection(vector_size)
        self._ensure_dual_collection(vector_size)
        self._ensure_unified_collection(vector_size)

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

    def _ensure_unified_collection(self, vector_size: int) -> None:
        """Cria collection unificada com payload indices para filtros."""
        collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.unified_collection not in collections:
            self.client.create_collection(
                collection_name=self.unified_collection,
                vectors_config=VectorParams(
                    size=vector_size, distance=Distance.COSINE
                ),
            )
            # Criar payload indices para filtros
            for field, schema in [
                ("category", PayloadSchemaType.KEYWORD),
                ("is_exclusive", PayloadSchemaType.BOOL),
                ("emotional_tone", PayloadSchemaType.KEYWORD),
                ("intensity", PayloadSchemaType.FLOAT),
                ("viral_potential", PayloadSchemaType.FLOAT),
                ("source", PayloadSchemaType.KEYWORD),
            ]:
                try:
                    self.client.create_payload_index(
                        collection_name=self.unified_collection,
                        field_name=field,
                        field_schema=schema,
                    )
                except Exception:
                    pass

    def index_unified(
        self,
        video_id: int,
        embedding: list[float],
        payload: dict,
    ) -> str:
        """Indexa embedding unificado com metadata rica. Retorna point ID."""
        point_id = video_id
        self.client.upsert(
            collection_name=self.unified_collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return str(point_id)

    def search_unified(
        self,
        query_embedding: list[float],
        limit: int = 20,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """
        Busca vetorial na collection unificada com filtros opcionais.

        Args:
            query_embedding: Embedding da query
            limit: Numero maximo de resultados
            filters: Dict com filtros (category, is_exclusive, intensity_min, etc.)

        Returns:
            Lista de resultados com id, score e payload
        """
        query_filter = self._build_filter(filters) if filters else None

        results = self.client.query_points(
            collection_name=self.unified_collection,
            query=query_embedding,
            query_filter=query_filter,
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

    def _build_filter(self, filters: dict) -> Optional[Filter]:
        """Converte dict de filtros em Qdrant Filter."""
        conditions = []

        if filters.get("category"):
            conditions.append(
                FieldCondition(key="category", match=MatchValue(value=filters["category"]))
            )
        if filters.get("is_exclusive") is not None:
            conditions.append(
                FieldCondition(key="is_exclusive", match=MatchValue(value=filters["is_exclusive"]))
            )
        if filters.get("emotional_tone"):
            conditions.append(
                FieldCondition(
                    key="emotional_tone", match=MatchValue(value=filters["emotional_tone"])
                )
            )
        if filters.get("source"):
            conditions.append(
                FieldCondition(key="source", match=MatchValue(value=filters["source"]))
            )

        # Range filters
        intensity_range = {}
        if filters.get("intensity_min") is not None:
            intensity_range["gte"] = filters["intensity_min"]
        if filters.get("intensity_max") is not None:
            intensity_range["lte"] = filters["intensity_max"]
        if intensity_range:
            conditions.append(
                FieldCondition(key="intensity", range=Range(**intensity_range))
            )

        viral_range = {}
        if filters.get("viral_potential_min") is not None:
            viral_range["gte"] = filters["viral_potential_min"]
        if filters.get("viral_potential_max") is not None:
            viral_range["lte"] = filters["viral_potential_max"]
        if viral_range:
            conditions.append(
                FieldCondition(key="viral_potential", range=Range(**viral_range))
            )

        if not conditions:
            return None

        return Filter(must=conditions)

    def find_similar(self, video_id: int, limit: int = 10) -> list[dict]:
        """
        Busca videos similares a um dado video usando seu embedding unificado.

        Args:
            video_id: ID do video de referencia
            limit: Numero maximo de resultados

        Returns:
            Lista de resultados similares (excluindo o proprio video)
        """
        try:
            points = self.client.retrieve(
                collection_name=self.unified_collection,
                ids=[video_id],
                with_vectors=True,
            )
            if not points:
                return []

            vector = points[0].vector
            results = self.client.query_points(
                collection_name=self.unified_collection,
                query=vector,
                limit=limit + 1,
                with_payload=True,
            )
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results.points
                if hit.id != video_id
            ][:limit]
        except Exception:
            return []

    def get_collection_stats(self) -> dict:
        """Retorna estatisticas de todas as collections."""
        stats = {}
        for name in [self.collection, self.dual_collection, self.unified_collection]:
            try:
                info = self.client.get_collection(name)
                stats[name] = {
                    "points_count": info.points_count or 0,
                    "vectors_count": getattr(info, 'vectors_count', None) or getattr(info, 'indexed_vectors_count', 0) or 0,
                }
            except Exception:
                stats[name] = {"points_count": 0, "vectors_count": 0}
        return stats

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
        """Remove ponto do Qdrant (todas as collections)."""
        for col in [self.collection, self.dual_collection, self.unified_collection]:
            try:
                self.client.delete(
                    collection_name=col,
                    points_selector=[video_id],
                )
            except Exception:
                pass
