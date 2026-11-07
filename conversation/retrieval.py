"""Custom retrieval step: embed the query and fetch the most similar document chunks."""

from collections.abc import Sequence

from core.llm import Embedder
from core.vector_store import SearchHit, VectorStore


class Retriever:
    def __init__(self, embedder: Embedder, vector_store: VectorStore, top_k: int) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._top_k = top_k

    def retrieve(self, query: str) -> list[SearchHit]:
        vector = self._embedder.embed_query(query)
        return self._vector_store.search(vector, limit=self._top_k)


def format_context(hits: Sequence[SearchHit]) -> str:
    """Render retrieved chunks as numbered excerpts the answer prompt can cite."""
    if not hits:
        return "(no relevant excerpts were found)"
    return "\n\n".join(
        f"[{number}] {hit.filename}, chunk {hit.chunk_index}\n{hit.text}"
        for number, hit in enumerate(hits, start=1)
    )
