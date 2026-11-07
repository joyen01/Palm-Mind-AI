"""Metadata for uploaded documents. Chunk text and vectors live in the vector store."""

import uuid

from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        INDEXED = "indexed", "Indexed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=8)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)
    chunking_strategy = models.CharField(max_length=32)
    chunk_size = models.PositiveIntegerField()
    chunk_overlap = models.PositiveIntegerField()
    chunk_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PROCESSING,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.filename
