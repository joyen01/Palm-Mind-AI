"""Tests for text chunking strategies."""

import pytest

from ingestion.chunking.factory import get_chunker
from ingestion.chunking.fixed_size import FixedSizeChunker
from ingestion.chunking.paragraph import ParagraphChunker


def test_fixed_size_chunker_basic() -> None:
    chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
    text = (
        "This is a sample document text used to verify the fixed-size chunking strategy. "
        "It splits the text into distinct chunks while cutting cleanly at whitespace."
    )
    chunks = chunker.split(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 60  # accommodates whitespace boundaries
        assert chunk.strip() == chunk


def test_fixed_size_chunker_empty_text() -> None:
    chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=20)
    assert chunker.split("") == []
    assert chunker.split("   ") == []


def test_paragraph_chunker_preserves_paragraphs() -> None:
    chunker = ParagraphChunker(chunk_size=200, chunk_overlap=30)
    text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph."
    chunks = chunker.split(text)
    assert len(chunks) >= 1
    combined = " ".join(chunks)
    assert "First paragraph" in combined
    assert "Second paragraph" in combined
    assert "Third paragraph" in combined


def test_paragraph_chunker_large_paragraph() -> None:
    chunker = ParagraphChunker(chunk_size=50, chunk_overlap=10)
    long_paragraph = (
        "Sentence one is brief. Sentence two has more details. Sentence three wraps up."
    )
    chunks = chunker.split(long_paragraph)
    assert len(chunks) > 1


def test_get_chunker_factory() -> None:
    fixed = get_chunker("fixed_size", chunk_size=100, chunk_overlap=20)
    assert isinstance(fixed, FixedSizeChunker)

    paragraph = get_chunker("paragraph", chunk_size=200, chunk_overlap=40)
    assert isinstance(paragraph, ParagraphChunker)

    with pytest.raises(ValueError, match="Unknown chunking strategy"):
        get_chunker("invalid_strategy", chunk_size=100, chunk_overlap=20)  # type: ignore[arg-type]
