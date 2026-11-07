"""Errors raised while ingesting a document. Messages are safe to return to API clients."""


class DocumentProcessingError(Exception):
    """Base class for documents that cannot be processed."""


class UnsupportedFileError(DocumentProcessingError):
    """The uploaded file type is not supported."""


class DocumentExtractionError(DocumentProcessingError):
    """Text could not be extracted from the uploaded document."""
