"""Resolve a chunking strategy name to its implementation."""

from ingestion.chunking.base import ChunkingStrategyName, TextChunker
from ingestion.chunking.fixed_size import FixedSizeChunker
from ingestion.chunking.paragraph import ParagraphChunker

_REGISTRY: dict[ChunkingStrategyName, type[TextChunker]] = {
    FixedSizeChunker.name: FixedSizeChunker,
    ParagraphChunker.name: ParagraphChunker,
}


def get_chunker(strategy: ChunkingStrategyName, chunk_size: int, chunk_overlap: int) -> TextChunker:
    chunker_cls = _REGISTRY.get(strategy)
    if chunker_cls is None:
        raise ValueError(f"Unknown chunking strategy: {strategy}")
    return chunker_cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
