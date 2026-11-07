"""HTTP endpoint for uploading and indexing documents."""

from typing import Any, cast

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ingestion.chunking.base import ChunkingStrategyName
from ingestion.exceptions import DocumentProcessingError
from ingestion.serializers import DocumentSerializer, DocumentUploadSerializer
from ingestion.services import build_ingestion_service


class DocumentUploadView(APIView):
    """POST a .pdf or .txt file. It is extracted, chunked, embedded and indexed."""

    def post(self, request: Request) -> Response:
        upload_serializer = DocumentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        validated: dict[str, Any] = upload_serializer.validated_data

        try:
            document = build_ingestion_service().ingest(
                upload=validated["file"],
                strategy=cast(ChunkingStrategyName, validated["chunking_strategy"]),
            )
        except DocumentProcessingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)
