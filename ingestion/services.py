from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.batching import batched
from core.llm import Embedder, get_embedder
from core.vector_store import ChunkRecord, VectorStore, get_vector_store
from ingestion.chunking.base import ChunkingStrategyName
from ingestion.chunking.factory import get_chunker
from ingestion.exceptions import DocumentExtractionError
from ingestion.extraction import detect_file_type, extract_text
from ingestion.models import Document

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 1000


class DocumentIngestionService:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        embedding_batch_size: int,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._embedding_batch_size = embedding_batch_size

    def ingest(self, upload: UploadedFile[bytes], strategy: ChunkingStrategyName) -> Document:
        filename = Path(upload.name or "upload").name
        file_type = detect_file_type(filename)
        content = _read_bytes(upload)

        document = Document.objects.create(
            filename=filename,
            file_type=file_type.value,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            chunking_strategy=strategy,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        try:
            text = extract_text(content, file_type)
            chunks = get_chunker(strategy, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP).split(text)
            if not chunks:
                raise DocumentExtractionError("The document contains no extractable text.")
            self._index(document, chunks)
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document.id)
            document.status = Document.Status.FAILED
            document.error_message = str(exc)[:MAX_ERROR_LENGTH]
            document.save(update_fields=["status", "error_message", "updated_at"])
            raise

        document.chunk_count = len(chunks)
        document.status = Document.Status.INDEXED
        document.save(update_fields=["chunk_count", "status", "updated_at"])
        return document

    def _index(self, document: Document, chunks: list[str]) -> None:
        self._vector_store.ensure_collection()
        vectors: list[list[float]] = []
        for batch in batched(chunks, self._embedding_batch_size):
            vectors.extend(self._embedder.embed(batch))

        records = [
            ChunkRecord(
                point_id=_chunk_point_id(str(document.id), index),
                vector=vector,
                payload={
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "chunk_index": index,
                    "chunking_strategy": document.chunking_strategy,
                    "text": text,
                },
            )
            for index, (text, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        self._vector_store.upsert(records)


def _read_bytes(upload: UploadedFile[bytes]) -> bytes:
    upload.seek(0)
    data = upload.read()
    return data if isinstance(data, bytes) else data.encode("utf-8")


def _chunk_point_id(document_id: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}/chunks/{index}"))


def build_ingestion_service() -> DocumentIngestionService:
    return DocumentIngestionService(
        embedder=get_embedder(),
        vector_store=get_vector_store(),
        embedding_batch_size=settings.EMBEDDING_BATCH_SIZE,
    )
