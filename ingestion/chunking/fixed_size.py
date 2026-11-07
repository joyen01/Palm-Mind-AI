"""Strategy 1: fixed-size character windows with overlap."""

from typing import ClassVar

from ingestion.chunking.base import ChunkingStrategyName, TextChunker


class FixedSizeChunker(TextChunker):
    """Slides a window of ``chunk_size`` characters, cutting at whitespace where possible."""

    name: ClassVar[ChunkingStrategyName] = "fixed_size"

    def split(self, text: str) -> list[str]:
        source = text.strip()
        chunks: list[str] = []
        start = 0
        while start < len(source):
            end = min(start + self.chunk_size, len(source))
            if end < len(source):
                end = _last_whitespace_before(source, start, end)
            piece = source[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(source):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks


def _last_whitespace_before(source: str, start: int, end: int) -> int:
    """Return the index of the last whitespace in the window's second half, else ``end``."""
    midpoint = start + (end - start) // 2
    for index in range(end - 1, midpoint, -1):
        if source[index].isspace():
            return index
    return end
