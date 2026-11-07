"""Base class and shared types for chunking strategies."""

from abc import ABC, abstractmethod
from typing import ClassVar, Literal

ChunkingStrategyName = Literal["fixed_size", "paragraph"]
CHUNKING_STRATEGY_CHOICES: tuple[ChunkingStrategyName, ...] = ("fixed_size", "paragraph")


class TextChunker(ABC):
    """Splits extracted text into chunks of at most ``chunk_size`` characters."""

    name: ClassVar[ChunkingStrategyName]

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= chunk_overlap <= chunk_size // 2:
            raise ValueError("chunk_overlap must be between 0 and half of chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def split(self, text: str) -> list[str]:
        """Return non-empty chunks, each at most ``chunk_size`` characters long."""
