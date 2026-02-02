"""
QdrantService - Indexacao e busca vetorial no Qdrant.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)


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
        self._ensure_collection(vector_size)

    def _ensure_collection(self, vector_size: int) -> None:
        """Cria collection se nao existir."""
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

    def index(
        self,
        video_id: int,
        embedding: list[float],
        payload: dict,
    ) -> str:
        """Indexa embedding com metadata. Retorna o point ID usado."""
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
        """Busca vetorial por similaridade coseno."""
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
        """Remove ponto do Qdrant."""
        self.client.delete(
            collection_name=self.collection,
            points_selector=[video_id],
        )
