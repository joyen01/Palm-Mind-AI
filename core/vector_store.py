"""Qdrant-backed vector storage for document chunks."""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from core.batching import batched

UPSERT_BATCH_SIZE = 256


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    """A chunk ready to be written: its point ID, embedding and payload."""

    point_id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A chunk returned by a similarity search."""

    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class VectorStore:
    """Repository over a single Qdrant collection holding every document chunk."""

    def __init__(self, client: QdrantClient, collection: str, dimensions: int) -> None:
        self._client = client
        self._collection = collection
        self._dimensions = dimensions

    def ensure_collection(self) -> None:
        """Create the collection, and an index on document_id, if they do not exist yet."""
        if self._client.collection_exists(self._collection):
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(
                size=self._dimensions,
                distance=qmodels.Distance.COSINE,
            ),
        )
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )

    def upsert(self, records: Sequence[ChunkRecord]) -> None:
        for batch in batched(records, UPSERT_BATCH_SIZE):
            points = [
                qmodels.PointStruct(
                    id=record.point_id,
                    vector=record.vector,
                    payload=record.payload,
                )
                for record in batch
            ]
            self._client.upsert(collection_name=self._collection, points=points, wait=True)

    def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        if not self._client.collection_exists(self._collection):
            return []
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [_to_hit(point) for point in response.points]


def _to_hit(point: qmodels.ScoredPoint) -> SearchHit:
    payload: dict[str, Any] = point.payload or {}
    return SearchHit(
        document_id=str(payload["document_id"]),
        filename=str(payload["filename"]),
        chunk_index=int(payload["chunk_index"]),
        text=str(payload["text"]),
        score=float(point.score),
    )


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=30,
    )
    return VectorStore(
        client=client,
        collection=settings.QDRANT_COLLECTION,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
