import re
from collections.abc import Iterator, Sequence
from typing import ClassVar

from ingestion.chunking.base import ChunkingStrategyName, TextChunker
from ingestion.chunking.fixed_size import FixedSizeChunker

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_SEPARATOR = "\n\n"


class ParagraphChunker(TextChunker):
    name: ClassVar[ChunkingStrategyName] = "paragraph"

    def split(self, text: str) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        for unit in self._units(text):
            if current and _joined_length([*current, unit]) > self.chunk_size:
                chunks.append(_SEPARATOR.join(current))
                current = self._carry_over(current, unit)
            current.append(unit)
        if current:
            chunks.append(_SEPARATOR.join(current))
        return chunks

    def _units(self, text: str) -> Iterator[str]:
        for paragraph in _PARAGRAPH_BREAK.split(text):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) <= self.chunk_size:
                yield paragraph
                continue
            for sentence in _SENTENCE_BREAK.split(paragraph):
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(sentence) <= self.chunk_size:
                    yield sentence
                else:
                    fallback = FixedSizeChunker(self.chunk_size, self.chunk_overlap)
                    yield from fallback.split(sentence)

    def _carry_over(self, previous: list[str], incoming: str) -> list[str]:
        tail: list[str] = []
        for unit in reversed(previous):
            candidate = [unit, *tail]
            if _joined_length(candidate) > self.chunk_overlap:
                break
            tail = candidate
        while tail and _joined_length([*tail, incoming]) > self.chunk_size:
            tail.pop(0)
        return tail


def _joined_length(units: Sequence[str]) -> int:
    return sum(len(unit) for unit in units) + len(_SEPARATOR) * (len(units) - 1)
