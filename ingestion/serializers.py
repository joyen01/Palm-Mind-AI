"""Request validation and response shapes for the ingestion API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from ingestion.chunking.base import CHUNKING_STRATEGY_CHOICES
from ingestion.extraction import SUPPORTED_EXTENSIONS
from ingestion.models import Document


class DocumentUploadSerializer(serializers.Serializer[Any]):
    file = serializers.FileField(help_text="A .pdf or .txt file.")
    chunking_strategy = serializers.ChoiceField(
        choices=list(CHUNKING_STRATEGY_CHOICES),
        default="fixed_size",
        help_text="fixed_size: character windows with overlap. paragraph: structure-aware.",
    )

    def validate_file(self, value: UploadedFile[bytes]) -> UploadedFile[bytes]:
        suffix = Path(value.name or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise serializers.ValidationError("Only .pdf and .txt files are supported.")
        if value.size is not None and value.size > settings.UPLOAD_MAX_BYTES:
            raise serializers.ValidationError(
                f"File exceeds the {settings.UPLOAD_MAX_BYTES}-byte upload limit."
            )
        return value


class DocumentSerializer(serializers.ModelSerializer[Document]):
    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "file_type",
            "size_bytes",
            "chunking_strategy",
            "chunk_size",
            "chunk_overlap",
            "chunk_count",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
